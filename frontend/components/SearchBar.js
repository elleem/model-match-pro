import { useModels } from '@/contexts/models';
import { usePrompts } from '@/contexts/prompts';
import { useSearch } from '@/contexts/search';
import { Form, FormGroup, Input, Label, Button } from 'reactstrap';

export default function SearchBar() {
  const { selectedModels } = useModels();

  const { searchText, setSearchText } = useSearch();
  const { createPrompt } = usePrompts();

  function handleSubmit() {
    createPrompt({ input_str: searchText, lang_models: selectedModels });
  }
  return (
    <Form>
      <FormGroup className="max-w-lg gap-1 mx-auto my-2">
        <Label for="prompt">Enter your prompt</Label>
        <Input
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          type="textarea"
          // type="text"
          name="prompt"
          id="prompt"
          rows={5}
          autofocus
          className="resize-y"
        />
        <Button
          color="primary"
          className="my-2"
          onClick={handleSubmit}
          type="button"
          disabled={!selectedModels.length}
        >
          Search
        </Button>
      </FormGroup>
    </Form>
  );
}
