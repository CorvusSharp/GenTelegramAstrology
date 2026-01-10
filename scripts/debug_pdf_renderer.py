from astro_bot.pdf_renderer import PDFReportGenerator
import os

def test_rendering():
    # Test case 1: [P] tag spanning multiple lines
    text_multiline = """[H1]Test 1[/H1]
[P]
This is a paragraph
that spans multiple
lines.
[/P]
"""
    
    # Test case 2: Concatenated tags [/P][P]
    text_concat = """[H1]Test 2[/H1]
[P]First paragraph.[/P][P]Second paragraph stuck to the first.[/P]
"""

    # Test case 3: Mixed content
    text_mixed = """[H1]Test 3[/H1]
[P]Normal paragraph.[/P]
[P]Paragraph with [B]bold[/B] text inside.[/P]
[P]Broken
line paragraph.[/P][P]Immediate next paragraph.[/P]
"""

    output_file = "debug_output.pdf"
    
    # Dummy client_data
    client_data = {
        "name": "Test User",
        "birth_date": "01.01.2000",
        "birth_time": "12:00",
        "birth_place": "Test City"
    }

    print("Generating PDF...")
    try:
        generator = PDFReportGenerator(output_filename=output_file)
        # The method creates the file internally using self.output_filename, 
        # but the signature might just return the filename.
        # Let's check if we need to pass output_filename in constructor.
        # Yes, passed in constructor.
        
        result_path = generator.create_pdf(client_data, text_mixed)
        print(f"Success! PDF generated at {result_path}")
        
        # Verify file exists and has size
        if os.path.exists(result_path) and os.path.getsize(result_path) > 0:
            print("File exists and is not empty.")
        else:
            print("File extraction failed.")
            
    except Exception as e:
        print(f"Error during PDF generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rendering()
