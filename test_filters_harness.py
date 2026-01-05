"""
test_filters_harness.py

Tiny manual harness to poke at the MemoryMuse filters.
Run with:  python test_filters_harness.py
"""

# TODO: update these imports to match your actual module / function names
# e.g. from relational_memory import apply_filters_to_text
from app.core.text_filters import get_text_filter_config, filter_text, TextFilterPurpose


# ---------- Sample Cases ----------

def get_test_cases():
    """
    Return a list of (label, text) tuples.
    You can edit/extend this freely.
    """
    cases = [
        (
            "simple_chat",
            "Hey Iris, can you remind me to take out the trash tomorrow at 8pm?"
        ),
        (
            "long_code_block",
            """Here is some code:
            
            ```python
            def example():
                for i in range(100):
                    print(i)
            cfg = CodeBlockFilterConfig(
                enabled=True,
                max_lines=20,
                mode=CodeBlockFilterMode.TRUNCATE,
                min_lines_for_filter=6,
                marker_text="/// shortened ///",
            )
            
            filtered = filter_code_blocks_by_lines(text, cfg)
            ```
            
            And some trailing explanation after the code.
            """
        ),
        (
            "json_payload",
            """{
              "command": "remember_fact",
              "text": "Tuesday night is Hogwarts game night.",
              "metadata": {
                "source": "user",
                "priority": "normal"
              }
            }"""
        ),
        (
            "mixed_markdown",
            """# Title

            Some intro text.
            
            ```json
            {"foo": "bar", "count": 3}
            ```
            
            More text after the JSON block.
            """
        ),
        (
            "tags",
            """
            This is a message with command output
            
            <command-response>This is a message to the user<internal-data>{"foo": "bar", "count": 3}</internal-data></command-response>
            
            Checking just command-response
            <command-response>this is inside command-response</command-response>
            
            And check just internal-data
            <internal-data>this is inside text</internal-data>
            
            <muse-experience>
            This is a message from Iris to herself that should remain
            </muse-experience>
            
            <remove-this-tag>
            This is a test for just tag removeal
            </remove-this-tag>
            

            """
        ),
        (
            "everything",
            """
            1. JSON:
            Now some json in code block
            ```json
            {"foo": "bar", "count": 3}
            ```
            Now some naked and nested json
            {
              "command": "remember_fact",
              "text": "Tuesday night is Hogwarts game night.",
              "metadata": {
                "source": "user",
                "priority": "normal"
              }
            }
            
            2. XML Block Removal
            <command-response>This is a message to the user<internal-data>{"foo": "bar", "count": 3}</internal-data></command-response>
            And checking only a start <command-response>

            3. XML Tag Stripping
            <remove-this-tag>This is inside the tags</remove-this-tag>

            4. Code blocks
                a. A short block
                ```python
                    def example():
                        for i in range(100):
                        print(i)
                ```
                b. An empty block with newlines
                ```
                
                
                ```
                c. An empty block without any lines
                ```
                ```
                d. An empty block with code type
                ```python
                ```
                e. A longer block
                ```python
                    def example():
                        for i in range(100):
                            print(i)
                        cfg = CodeBlockFilterConfig(
                        enabled=True,
                        max_lines=20,
                        mode=CodeBlockFilterMode.TRUNCATE,
                            min_lines_for_filter=6,
                        marker_text="/// shortened ///",
                    )
                    filtered = filter_code_blocks_by_lines(text, cfg)
                    def example():
                        for i in range(100):
                            print(i)
                        cfg = CodeBlockFilterConfig(
                        enabled=True,
                        max_lines=20,
                        mode=CodeBlockFilterMode.TRUNCATE,
                        min_lines_for_filter=6,
                        marker_text="/// shortened ///",
                    )
                    filtered = filter_code_blocks_by_lines(text, cfg)
                    def example():
                        for i in range(100):
                            print(i)
                        cfg = CodeBlockFilterConfig(
                        enabled=True,
                        max_lines=20,
                        mode=CodeBlockFilterMode.TRUNCATE,
                        min_lines_for_filter=6,
                        marker_text="/// shortened ///",
                    )
                    filtered = filter_code_blocks_by_lines(text, cfg)
                ```
            """
        )
        # Add your own below:
        # ("my_custom_case", "paste your test text here"),
    ]
    return cases


# ---------- Harness Logic ----------


def pretty_print_case(label, original, filtered):
    """
    Print a readable before/after diff for one case.
    """
    separator = "=" * 80
    print(separator)
    print(f"[CASE] {label}")
    print("-" * 80)
    print("ORIGINAL:")
    print(original)
    print("-" * 80)
    print("FILTERED:")
    print(filtered)
    print(separator)
    print()


def run_case(label, text):
    """
    Run a single test case through the filters and print results.
    """
    cfg = get_text_filter_config("MNEMOSYNE", "EMBEDDING", "DEFAULT")
    try:
        filtered = filter_text(text, cfg)
    except Exception as e:
        print(f"[ERROR] While processing case '{label}': {e}")
        return

    pretty_print_case(label, text, filtered)


def run_all_cases():
    """
    Run all defined test cases.
    """
    cases = get_test_cases()
    for label, text in cases:
        run_case(label, text)


def run_interactive():
    """
    Optional: quick interactive mode so you can paste text on the fly.
    """


    print("Interactive filter harness. Paste text and press Enter twice to run.")
    print("Type /quit on a line by itself to exit.\n")

    buffer = []
    while True:
        line = input()
        if line.strip() == "/quit":
            break
        if line == "":
            if not buffer:
                continue
            text = "\n".join(buffer)
            buffer.clear()
            print("\n[RUNNING FILTERS...]\n")
            try:
                cfg = get_text_filter_config("SEARCH", "EMBEDDING", "NOCODE")
                filtered = filter_text(text, cfg)
            except Exception as e:
                print(f"[ERROR] {e}")
                continue
            pretty_print_case("interactive", text, filtered)
            print("Paste next block (or /quit):")
        else:
            buffer.append(line)


if __name__ == "__main__":
    # Choose your mode here:
    # 1) Run all predefined cases
    run_all_cases()

    # 2) Or comment the above and use interactive mode instead:
    #run_interactive()