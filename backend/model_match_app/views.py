import asyncio

from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from .models import LLM, Prompt, Responses
from .permissions import IsOwnerOrReadOnly
from .serializers import LLMSerializer, PromptSerializer, ResponsesSerializer

from rest_framework import status
import httpx

import environ
env = environ.Env()
environ.Env.read_env()

API_TOKEN = env("API_TOKEN", default=None)

if not API_TOKEN:
    raise ValueError("API_TOKEN is not set in .env file.")

HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}
BASE_API_URL = "https://api-inference.huggingface.co/models/"


# async def make_api_call(api_code, query):
#     # construct the complete API URL using the model's api_code
#     api_url = f"{BASE_API_URL}{api_code}"
#     # build the payload per docs
#     payload = {"inputs": query}
#     async with httpx.AsyncClient(follow_redirects=False) as client:
#         # make the api request
#         response = await client.post(api_url, headers=HEADERS, json=payload)
#     if response.status_code == 302:
#         redirect_url = response.headers.get('Location')
#         print("Redirecting to:", redirect_url)
#     # error handling
#     if response.status_code != 200:
#         error_message = f"API call failed for model {api_code} with status code {response.status_code}: {response.text}"
#         return None, error_message
#
#     return response.json(), None

def make_api_call(api_code, input_str):
    api_url = f"{BASE_API_URL}{api_code}"
    payload = {"inputs": input_str}

    print(f"Making API call to {api_url} with query: {input_str}")
    with httpx.Client() as client:
        response = client.post(api_url, headers=HEADERS, json=payload)
    print(f"Received status code {response.status_code} from {api_url}")
    if response.status_code == 302:
        redirect_url = response.headers.get('Location')
        print("Redirecting to:", redirect_url)

    if response.status_code != 200:
        error_message = f"API call failed for model {api_code} with status code {response.status_code}: {response.text}"
        return None, error_message

    api_response = response.json()
    print(f"Received API response: {api_response}")

    return api_response, None


# lists and creates prompts
class PromptList(ListCreateAPIView):
    permission_classes = (IsOwnerOrReadOnly,)
    serializer_class = PromptSerializer

    def get_queryset(self):
        user = self.request.user
        return Prompt.objects.filter(user_id=user)

    def create(self, request, *args, **kwargs):
        print("Creating a new prompt...")
        response = super(PromptList, self).create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            self.create_responses(response, request, *args, **kwargs)
        return response
    # def create(self, request, *args, **kwargs):
    #     response = super(PromptList, self).create(request, *args, **kwargs)
    #     # response = self.create(request, *args, **kwargs)
    #     # if the prompt is successful
    #     if response.status_code == status.HTTP_201_CREATED:
    #         loop = asyncio.new_event_loop()
    #         asyncio.set_event_loop(loop)
    #         try:
    #             loop.run_until_complete(self.async_create(
    #                 response, request, *args, **kwargs))
    #         finally:
    #             loop.close()
    #     return response

    # async def async_create(self, response, request, *args, **kwargs):
    #
    #     # Assuming the primary key field is named 'id'
    #     input_str = response.data.get('input_str')
    #     lang_models = response.data.get('lang_models')
    #     # prompt = Prompt.objects.get(pk=input_str)
    #     prompt = Prompt.objects.create(
    #         user_id_id=self.request.user.id, input_str=input_str, lang_models=lang_models)
    #     # prompt = self.object
    #
    #     # print("PROMPT")
    #     # print(prompt)
    #     # print(prompt.__dir__())
    #     # print("REQUEST")
    #     # print(prompt.request)
    #     # to collect error messages
    #     error_messages = []
    #
    #     for model_id in lang_models:
    #         lang_model = LLM.objects.get(pk=model_id)
    #
    #         # use prompt.input_str as the query to be sent to the api
    #         api_response, error = await make_api_call(lang_model.api_code, input_str)
    #
    #         # save the response
    #         # api_response['generated_text'] per the actual structure of huggingface
    #         if api_response:
    #             Responses.objects.create(
    #                 prompt_id=prompt.pk, lang_model_id=lang_model, response=api_response['generated_text'])
    #         else:
    #             error_messages.append(error)
    #     # if any of the models have issues, returns a summary message, and a list of error messages for the individual models, otherwise return normally
    #     if error_messages:
    #         custom_data = {
    #             'status': 'Some models did not return results.',
    #             'errors': error_messages
    #         }
    #         response.data.update(custom_data)
    def create_responses(self, response, request, *args, **kwargs):
        print("Creating responses for the prompt...")
        input_str = response.data.get('input_str')
        print(input_str)
        print(response.data)
        lang_models = response.data.get('lang_models')
        print(lang_models)
        prompt = Prompt.objects.create(
            user_id_id=self.request.user.id, input_str=input_str, lang_models=lang_models)

        error_messages = []
        api_responses_list = []  # List to accumulate API responses
        print("About to enter the loop with lang_models:", lang_models)
        for model_id in lang_models:
            lang_model = LLM.objects.get(pk=model_id)
            print("Processing lang_model with ID:", model_id,
                  "and API code:", lang_model.api_code)
            api_response, error = make_api_call(lang_model.api_code, input_str)

            if api_response:
                # Please help fix the following err:
                # TypeError at /api/v1/model_match_app/prompts/
                # list indices must be integers or slices, not str
                Responses.objects.create(
                    prompt_id=prompt.pk, lang_model_id=lang_model, response=api_response['generated_text'])
                # Append the response to the list
                api_responses_list.append(api_response['generated_text'])
            else:
                error_messages.append(error)

        if error_messages:
            custom_data = {
                'status': 'Some models did not return results.',
                'errors': error_messages
            }
            response.data.update(custom_data)

        # At this point, api_responses_list contains all the API responses
        print(api_responses_list)  # For debugging purposes


# allows user to edit individual responses
class PromptDetail(RetrieveUpdateDestroyAPIView):
    permission_classes = (IsOwnerOrReadOnly,)
    serializer_class = PromptSerializer

    def get_queryset(self):
        user = self.request.user
        return Prompt.objects.filter(user_id=user)


class ResponseList(ListAPIView):  # lists responses specific to a single prompt
    permission_classes = (IsOwnerOrReadOnly,)
    serializer_class = ResponsesSerializer

    def get_queryset(self):
        user = self.request.user
        prompt_pk = self.kwargs['pk']
        return Responses.objects.filter(prompt_id__user_id=user, prompt_id=prompt_pk)


class LLMList(ListAPIView):
    queryset = LLM.objects.all()
    serializer_class = LLMSerializer
