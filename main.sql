  IMPORTANT: RETURN ONLY THE SEARCH/REPLACE BLOCKS. NO EXPLANATIONS OR COMMENTS.
    USE THE FOLLOWING FORMAT FOR EACH BLOCK:

    <SEARCH>
    Code to be replaced
    </SEARCH>
    <REPLACE>
    New code to insert
    </REPLACE>

    If no changes are needed, return an empty list.
    """

    response = client.messages.create(
        model=CODEEDITORMODEL,
        max_tokens=8000,
        system=system_prompt,
        extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
        messages=[{"role": "user", "content": "Generate SEARCH/REPLACE blocks for the necessary changes."}]
    )

    code_editor_tokens['input'] += response.usage.input_tokens
    code_editor_tokens['output'] += response.usage.output_tokens

    # Parse the response to extract SEARCH/REPLACE blocks
    edit_instructions = parse_search_replace_blocks(response.content[0].text)

    # Update code editor memory (this is the only part that maintains some context between calls)
    code_editor_memory.append(f"Edit Instructions:\n{response.content[0].text}")

    return edit_instructions

except Exception as e:
    console.print(f"Error in generating edit instructions: {str(e)}", style="bold red")
    return []  # Return empty list if any exception occurs