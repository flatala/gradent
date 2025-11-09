"""Test script for the exam API workflow."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from workflows.exam_api import exam_api_graph, ExamAPIState

# Load environment variables from .env file
load_dotenv()

async def test_exam_api_workflow():
    """Test the exam API workflow with sample data."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    model_name = "meta-llama/llama-4-scout:free"  # More reliable free model

    print("=" * 80)
    print("Testing Exam API Workflow")
    print("=" * 80)
    
    # Get PDF paths
    pdf_paths = ['/Users/mflodzinski/Projects/gradent/W2S1-CF Neighborhood Models-6.pdf']
    question_header = 'Midterm Exam Recommender Systems'
    question_description = 'Generate 10 multiple choice questions'
    api_base_url = "http://localhost:3000"
        
    # Create state
    print("\n" + "=" * 80)
    print("Configuration:")
    print(f"  PDFs: {len(pdf_paths)} file(s)")
    for i, path in enumerate(pdf_paths, 1):
        print(f"    {i}. {Path(path).name}")
    print(f"  Header: {question_header}")
    print(f"  Description: {question_description}")
    print(f"  API: {api_base_url}")
    if model_name:
        print(f"  Model: {model_name}")
    print("=" * 80)
    
    # Create initial state
    state = ExamAPIState(
        pdf_paths=pdf_paths,
        question_header=question_header,
        question_description=question_description,
        api_key=api_key,
        api_base_url=api_base_url,
        model_name=model_name,
    )
    
    # Run workflow
    print("\n🚀 Starting workflow...")
    print("-" * 80)
    
    try:
        result = await exam_api_graph.ainvoke(state)
        
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        
        # Handle both dict and object results
        if isinstance(result, dict):
            error = result.get("error")
            uploaded_files = result.get("uploaded_files")
            generated_questions = result.get("generated_questions")
        else:
            error = result.error
            uploaded_files = result.uploaded_files
            generated_questions = result.generated_questions
        
        if error:
            print(f"\n❌ Error: {error}\n")
            return
        
        if uploaded_files:
            print(f"\n✅ Uploaded {len(uploaded_files)} file(s):")
            for f in uploaded_files:
                print(f"   - {f}")
        
        if generated_questions:
            print("\n✅ Successfully generated exam questions!\n")
            print("=" * 80)
            print(generated_questions)
            print("=" * 80)
            
            # Offer to save
            save = input("\nSave to file? (y/n): ").strip().lower()
            if save == 'y':
                output_file = input("Output filename (press Enter for 'generated_exam.md'): ").strip() or "generated_exam.md"
                output_path = Path(output_file)
                output_path.write_text(generated_questions)
                print(f"✅ Saved to: {output_path.absolute()}")
        else:
            print("\n⚠️  No questions were generated")
        
    except Exception as e:
        print(f"\n❌ Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_simple():
    """Simple hardcoded test (modify values below)."""
    
    print("Running simple hardcoded test...\n")
    api_key="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"

    state = ExamAPIState(
        pdf_paths=[
            "W2S1-CF Neighborhood Models-6.pdf",
        ],
        question_header="Test Exam",
        question_description="Generate 5 multiple choice questions",
        api_key=api_key,
        api_base_url="http://localhost:3000",
    )
    
    if not state.pdf_paths:
        print("❌ No PDF paths configured in test_simple()")
        print("   Edit this file and add PDF paths to test")
        return
    
    print(f"Uploading {len(state.pdf_paths)} PDF(s)...")
    result = await exam_api_graph.ainvoke(state)
    
    if isinstance(result, dict):
        error = result.get("error")
        questions = result.get("generated_questions")
    else:
        error = result.error
        questions = result.generated_questions
    
    if error:
        print(f"❌ Error: {error}")
    elif questions:
        print("✅ Success!\n")
        print(questions)
        
        # Auto-save to file
        output_path = Path("_results/generated_exam.md")
        output_path.write_text(questions)
        print(f"\n📝 Saved to: {output_path.absolute()}")
    else:
        print("⚠️  No questions generated")


if __name__ == "__main__":
    print("\nExam API Workflow Test")
    print("=" * 80)
    print("1. Interactive test (with prompts)")
    print("2. Simple test (hardcoded values)")
    print("=" * 80)
    
    choice = input("Choose test mode (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_exam_api_workflow())
    elif choice == "2":
        asyncio.run(test_simple())
    else:
        print("Invalid choice")
