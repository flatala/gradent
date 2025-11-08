"""Nodes for the assignment assessment workflow."""
import json
from typing import Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from shared.config import Configuration
from shared.utils import get_orchestrator_llm, get_text_llm
from .state import AssessmentState, AssessmentResult
from . import prompts


async def initialize_assessment(
    state: AssessmentState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Initialize the assessment workflow with system prompt and assignment details."""
    from vector_db.retrieval import retrieve_assignment_context
    
    info = state.assignment_info
    
    # Build description from available info
    description = info.description or info.raw_text or "No detailed description provided."
    
    # Retrieve relevant context from vector DB if assignment_id or course_id is available
    retrieved_context = None
    if info.assignment_id or info.course_id:
        try:
            # Build query from assignment info
            query = f"{info.title} {description[:500]}"
            
            retrieved_context = retrieve_assignment_context(
                query=query,
                assignment_id=info.assignment_id,
                course_id=info.course_id,
                user_id=state.user_id,
                top_k=3,  # Get top 3 most relevant chunks
                source_types=["assignment", "rubric", "lecture"]
            )
            
            if retrieved_context and retrieved_context != "No relevant context found in course materials.":
                print(f"✓ Retrieved {len(retrieved_context)} chars of context from vector DB")
            else:
                retrieved_context = None
        except Exception as e:
            print(f"Warning: Could not retrieve context from vector DB: {e}")
            retrieved_context = None
    
    # Build analysis prompt with optional context
    analysis_content = prompts.ANALYSIS_PROMPT.format(
        title=info.title,
        course_name=info.course_name or "Unknown",
        due_date=info.due_date.strftime("%Y-%m-%d %H:%M") if info.due_date else "Not specified",
        description=description
    )
    
    # Add retrieved context if available
    if retrieved_context:
        analysis_content += f"\n\n## Additional Context from Course Materials\n\n{retrieved_context}"
    
    messages = [
        SystemMessage(content=prompts.SYSTEM_PROMPT),
        HumanMessage(content=analysis_content),
    ]
    
    return {
        "messages": messages,
        "retrieved_context": retrieved_context
    }


async def analyze_assignment(
    state: AssessmentState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Agent analyzes the assignment and thinks through the assessment.
    
    This node uses the orchestrator LLM for reasoning about the assignment.
    """
    cfg = Configuration.from_runnable_config(config)
    llm = get_orchestrator_llm(cfg)
    
    # Get analysis from LLM
    response = await llm.ainvoke(state.messages)
    
    return {"messages": [response]}


async def generate_structured_assessment(
    state: AssessmentState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Generate the final structured assessment in JSON format.
    
    This node uses the text LLM with structured output.
    """
    cfg = Configuration.from_runnable_config(config)
    llm = get_text_llm(cfg)
    
    # Add structured output request
    messages = state.messages + [
        HumanMessage(content=prompts.STRUCTURED_OUTPUT_PROMPT)
    ]
    
    # Get structured response
    response = await llm.ainvoke(messages)
    
    # Parse the assessment JSON
    try:
        content = response.content
        
        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        assessment_data = json.loads(content)
        assessment = AssessmentResult(**assessment_data)
        
        return {
            "assessment": assessment,
            "messages": [response],
        }
    
    except Exception as e:
        # Fallback: create a basic assessment
        print(f"Warning: Failed to parse assessment JSON: {e}")
        print(f"Response content: {response.content[:500]}")
        
        return {
            "assessment": AssessmentResult(
                effort_hours_low=5.0,
                effort_hours_most=10.0,
                effort_hours_high=15.0,
                difficulty_1to5=3.0,
                risk_score_0to100=50.0,
                confidence_0to1=0.3,
                summary=f"Failed to generate structured assessment: {str(e)}",
                deliverables=[state.assignment_info.title],
            ),
            "messages": [response],
        }


async def save_to_database(
    state: AssessmentState, *, config: Optional[RunnableConfig] = None
) -> Dict:
    """Save the assessment to the database.
    
    This creates a new AssignmentAssessment record linked to the assignment.
    """
    from database import get_db_session, Assignment, AssignmentAssessment
    
    if not state.assessment:
        return {"assessment_record_id": None}
    
    info = state.assignment_info
    assessment = state.assessment
    
    # Get configuration
    cfg = Configuration.from_runnable_config(config)
    
    try:
        with get_db_session() as db:
            # If assignment_id is provided, use it; otherwise we'd need to create/find the assignment
            if not info.assignment_id:
                print("Warning: No assignment_id provided, skipping database save")
                return {"assessment_record_id": None}
            
            # Mark previous assessments as not latest
            db.query(AssignmentAssessment).filter(
                AssignmentAssessment.assignment_id == info.assignment_id,
                AssignmentAssessment.is_latest == True
            ).update({"is_latest": False})
            
            # Get version number
            max_version = db.query(AssignmentAssessment).filter(
                AssignmentAssessment.assignment_id == info.assignment_id
            ).count()
            
            # Create new assessment record
            record = AssignmentAssessment(
                assignment_id=info.assignment_id,
                version=max_version + 1,
                is_latest=True,
                effort_hours_low=assessment.effort_hours_low,
                effort_hours_most=assessment.effort_hours_most,
                effort_hours_high=assessment.effort_hours_high,
                difficulty_1to5=assessment.difficulty_1to5,
                weight_in_course=assessment.weight_in_course,
                risk_score_0to100=assessment.risk_score_0to100,
                confidence_0to1=assessment.confidence_0to1,
                milestones=assessment.milestones,
                prereq_topics=assessment.prereq_topics,
                deliverables=assessment.deliverables,
                blocking_dependencies=assessment.blocking_dependencies,
                sources=[],  # TODO: Add vector DB sources when implemented
                model_meta={
                    "model": cfg.orchestrator_model,
                    "text_model": cfg.text_model,
                }
            )
            
            db.add(record)
            db.flush()
            
            record_id = record.id
            print(f"✓ Saved assessment to database (ID: {record_id}, version: {record.version})")
            
            return {"assessment_record_id": record_id}
    
    except Exception as e:
        print(f"Error saving assessment to database: {e}")
        return {"assessment_record_id": None}
