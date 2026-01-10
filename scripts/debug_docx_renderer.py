from astro_bot.docx_renderer import DOCXReportGenerator
import os

def test_docx_rendering():
    # Test case: Mixed content with multi-line tags and concatenated tags
    text_mixed = """[H1]Test DOCX Fix[/H1]
[P]Normal paragraph.[/P]
[P]
Paragraph spanning
multiple lines.
[/P]
[P]Broken line block.[/P][P]Immediate next paragraph.[/P]
"""

    output_file = "debug_output.docx"
    
    # Dummy client_data
    client_data = {
        "name": "Test User",
        "birth_date": "01.01.2000",
        "birth_time": "12:00",
        "birth_place": "Test City"
    }

    print("Generating DOCX...")
    try:
        generator = DOCXReportGenerator(output_filename=output_file)
        result_path = generator.create_docx(client_data, text_mixed)
        print(f"Success! DOCX generated at {result_path}")
        
        # Verify file exists and has size
        if os.path.exists(result_path) and os.path.getsize(result_path) > 0:
            print("File exists and is not empty.")
        else:
            print("File extraction failed.")
            
    except Exception as e:
        print(f"Error during DOCX generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_docx_rendering()
