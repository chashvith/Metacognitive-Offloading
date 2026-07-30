"""Unit and Integration Test Suite for Recommendation Engine Subsystem."""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    HintLevelEnum,
    TeachingStrategy,
)
from services.recommendation.context_builder import RecommendationContextBuilder
from services.recommendation.policy_engine import PolicyEngine
from services.recommendation.knowledge_base import ConceptKnowledgeBase
from services.recommendation.prompt_builder import StructuredPromptBuilder
from services.recommendation.response_generator import TemplateGenerator
from services.recommendation.llm_generator import LLMGenerator
from services.recommendation.validator import RecommendationValidator
from services.recommendation.recommendation_service import recommendation_service


def test_context_builder():
    print("\n[1/7] Testing ContextBuilder...")
    builder = RecommendationContextBuilder()

    # Case A: Explicit parameters
    req_a = RecommendationRequest(
        problem_name="Two Sum",
        topic="Arrays",
        subtopic="HashMaps",
        difficulty="Easy",
        language="java",
        student_code="public int[] twoSum(int[] nums, int target) {}",
        solver_prediction="Needs Help",
        solver_confidence=0.91,
        hint_prediction="Concept Hint",
        hint_confidence=0.88
    )
    ctx_a = builder.build_context(req_a)

    assert ctx_a.problem.problem_name == "Two Sum"
    assert ctx_a.problem.topic == "Arrays"
    assert ctx_a.problem.subtopic == "HashMaps"
    assert ctx_a.problem.language == "java"
    assert ctx_a.student.student_code.startswith("public int[]")
    assert ctx_a.prediction.solver_prediction == "Needs Help"
    assert ctx_a.prediction.hint_prediction == "Concept Hint"
    assert ctx_a.prediction.normalized_hint_level == HintLevelEnum.CONCEPT
    print("  [OK] ContextBuilder explicit payload build PASSED.")

    # Case B: Telemetry snapshot payload with auto ML invocation
    req_b = RecommendationRequest(
        snapshot={
            "problem_name": "Contains Duplicate",
            "topic": "HashMaps",
            "subtopic": "Fundamentals",
            "current_struggle_score": 0.65,
            "compile_errors": 4
        }
    )
    ctx_b = builder.build_context(req_b)
    assert ctx_b.problem.problem_name == "Contains Duplicate"
    assert ctx_b.session.struggle_score == 0.65
    assert ctx_b.prediction.solver_prediction is not None
    assert ctx_b.prediction.hint_prediction is not None
    print("  [OK] ContextBuilder telemetry snapshot build PASSED.")


def test_policy_engine():
    print("\n[2/7] Testing PolicyEngine (Strict ML Hint Level Preservation)...")
    policy = PolicyEngine()
    builder = RecommendationContextBuilder()

    levels_to_test = [
        ("No Hint", HintLevelEnum.NO_HINT, False),
        ("Concept Hint", HintLevelEnum.CONCEPT, False),
        ("Guided Hint", HintLevelEnum.GUIDED, False),
        ("Pseudocode", HintLevelEnum.PSEUDOCODE, False),
        ("Full Solution", HintLevelEnum.FULL_SOLUTION, True),
    ]

    for raw_label, expected_enum, expect_code in levels_to_test:
        req = RecommendationRequest(
            problem_name="Test Problem",
            hint_prediction=raw_label
        )
        ctx = builder.build_context(req)
        strat = policy.determine_strategy(ctx)
        assert strat.hint_level == expected_enum, f"Expected {expected_enum}, got {strat.hint_level}"
        assert strat.allow_code == expect_code, f"Code permission mismatch for {raw_label}"
        assert strat.require_reflection_question is True
    print("  [OK] PolicyEngine hint level mappings PASSED for all 5 levels.")


def test_knowledge_base():
    print("\n[3/7] Testing ConceptKnowledgeBase...")
    kb = ConceptKnowledgeBase()

    # Test arrays/fundamentals concept lookup
    data_arrays = kb.get_concept("Arrays", "Fundamentals")
    assert "concept_id" in data_arrays
    assert "explanation" in data_arrays
    assert "hints" in data_arrays
    print("  [OK] ConceptKnowledgeBase Array fundamentals lookup PASSED.")

    # Test hashmap concept lookup
    data_hashmap = kb.get_concept("HashMaps", "Fundamentals")
    assert "HashMap" in data_hashmap.get("name", "") or "Hash" in data_hashmap.get("explanation", "")
    print("  [OK] ConceptKnowledgeBase HashMap fundamentals lookup PASSED.")

    # Test fallback to default concept for unknown topic
    data_unknown = kb.get_concept("Quantum Computing", "Superposition")
    assert data_unknown is not None
    assert "concept_id" in data_unknown
    print("  [OK] ConceptKnowledgeBase fallback PASSED.")


def test_prompt_builder():
    print("\n[4/7] Testing StructuredPromptBuilder...")
    prompt_builder = StructuredPromptBuilder()
    context_builder = RecommendationContextBuilder()
    policy_engine = PolicyEngine()
    kb = ConceptKnowledgeBase()

    req = RecommendationRequest(
        problem_name="Two Sum",
        topic="HashMaps",
        subtopic="Fundamentals",
        hint_prediction="Concept Hint"
    )
    ctx = context_builder.build_context(req)
    strat = policy_engine.determine_strategy(ctx)
    concept_data = kb.get_concept(ctx.problem.topic, ctx.problem.subtopic)

    prompt = prompt_builder.build_prompt(ctx, strat, concept_data)
    assert prompt.system_instruction is not None
    assert "Two Sum" in prompt.problem_context_summary
    assert prompt.teaching_strategy.hint_level == HintLevelEnum.CONCEPT
    assert prompt.formatting_requirements["hint_level"] == "concept"
    print("  [OK] StructuredPromptBuilder prompt generation PASSED.")


def test_response_generator():
    print("\n[5/7] Testing Response Generators...")
    template_gen = TemplateGenerator()
    llm_gen = LLMGenerator()

    context_builder = RecommendationContextBuilder()
    policy_engine = PolicyEngine()
    kb = ConceptKnowledgeBase()
    prompt_builder = StructuredPromptBuilder()

    # Test Concept Hint Template Generation
    req_concept = RecommendationRequest(
        problem_name="Two Sum",
        topic="HashMaps",
        subtopic="Fundamentals",
        language="python",
        hint_prediction="Concept Hint"
    )
    ctx_concept = context_builder.build_context(req_concept)
    strat_concept = policy_engine.determine_strategy(ctx_concept)
    concept_data = kb.get_concept(ctx_concept.problem.topic, ctx_concept.problem.subtopic)
    prompt_concept = prompt_builder.build_prompt(ctx_concept, strat_concept, concept_data)

    res_concept = template_gen.generate(prompt_concept, ctx_concept, concept_data)
    assert res_concept.level == "concept"
    assert res_concept.code is None
    assert res_concept.complexity is None
    assert res_concept.reflection_question is not None
    print("  [OK] TemplateGenerator Concept Hint PASSED.")

    # Test Full Solution Template Generation
    req_full = RecommendationRequest(
        problem_name="Two Sum",
        topic="HashMaps",
        subtopic="Fundamentals",
        language="python",
        hint_prediction="Full Solution"
    )
    ctx_full = context_builder.build_context(req_full)
    strat_full = policy_engine.determine_strategy(ctx_full)
    prompt_full = prompt_builder.build_prompt(ctx_full, strat_full, concept_data)

    res_full = template_gen.generate(prompt_full, ctx_full, concept_data)
    assert res_full.level == "full_solution"
    assert res_full.code is not None
    assert res_full.complexity is not None
    print("  [OK] TemplateGenerator Full Solution PASSED.")

    # Test LLMGenerator wrapper delegation
    res_llm = llm_gen.generate(prompt_full, ctx_full, concept_data)
    assert res_llm.level == "full_solution"
    assert res_llm.title is not None
    print("  [OK] LLMGenerator wrapper delegation PASSED.")


def test_validator():
    print("\n[6/7] Testing RecommendationValidator Guardrails...")
    validator = RecommendationValidator()

    # Case A: Violating Concept level by attaching code
    strat_concept = TeachingStrategy(hint_level=HintLevelEnum.CONCEPT, allow_code=False)
    bad_res = RecommendationResponse(
        title="Concept Hint",
        level="concept",
        message="Concept msg",
        next_step="Next step",
        reflection_question="Reflection?",
        encouragement="Keep going",
        confidence=0.9,
        code="def leaked_solution(): pass",
        complexity={"time": "O(1)"}
    )

    clean_res = validator.validate(bad_res, strat_concept)
    assert clean_res.code is None, "Validator failed to sanitize leaked code!"
    assert clean_res.complexity is None, "Validator failed to sanitize leaked complexity!"
    print("  [OK] RecommendationValidator code leakage sanitization PASSED.")


def test_end_to_end_recommendation_service():
    print("\n[7/7] Testing RecommendationService End-to-End Orchestration...")

    # Input payload matching prompt specification
    input_payload = {
        "problem_name": "Two Sum",
        "difficulty": "Easy",
        "topic": "Arrays",
        "subtopic": "HashMaps",
        "language": "Java",
        "student_code": "public int[] twoSum(int[] nums, int target) { return new int[0]; }",
        "solver_prediction": "Needs Help",
        "solver_confidence": 0.91,
        "hint_prediction": "Concept Hint",
        "hint_confidence": 0.88
    }

    response = recommendation_service.recommend(input_payload)

    assert isinstance(response, RecommendationResponse)
    assert response.status == "success"
    assert response.level == "concept"
    assert response.confidence == 0.88
    assert response.code is None
    assert response.complexity is None
    assert response.reflection_question is not None
    assert len(response.message) > 0
    assert len(response.next_step) > 0
    assert len(response.encouragement) > 0
    assert response.metadata["problem_name"] == "Two Sum"
    assert response.metadata["generator_type"] == "TemplateGenerator"

    print("  [OK] End-to-End RecommendationService Orchestration PASSED!")
    print("\nSample Generated Recommendation Output JSON:\n")
    print(response.model_dump_json(indent=2))


def run_all_tests():
    print("=" * 70)
    print("STARTING RECOMMENDATION ENGINE SUBSYSTEM TEST SUITE")
    print("=" * 70)
    test_context_builder()
    test_policy_engine()
    test_knowledge_base()
    test_prompt_builder()
    test_response_generator()
    test_validator()
    test_end_to_end_recommendation_service()
    print("=" * 70)
    print("ALL RECOMMENDATION ENGINE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
