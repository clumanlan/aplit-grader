import uuid

import pytest
from sqlalchemy import select

from aplit_grader.schemas.rubric import CriterionResult
from aplit_grader.services.rubric import RUBRIC
from aplit_grader.storage.db import (
    Database,
    DisputeNotFoundError,
    EssayAccessDeniedError,
    EssayNotFoundError,
    RawGradeMismatchError,
)
from aplit_grader.storage.models import (
    AcceptedGrade,
    Dispute,
    DisputeMessageRow,
    Essay,
    GradingSession,
    RawGrade,
)

pytestmark = pytest.mark.db

TEACHER_ID = "teacher-1"
CLASS_ID = "Period 3 — AP Lit"
RUN_ID = "run-1"


def _criterion(criterion_id="bp1-evidence-1", score=2, missing=False, sentence_refs=None) -> CriterionResult:
    return CriterionResult(
        criterion_id=criterion_id,
        score=score,
        missing=missing,
        strengths=["Quote is relevant."],
        critiques=["Missing context."],
        reasoning="Some reasoning.",
        sentence_refs=sentence_refs or [1],
    )


def _all_fourteen_criteria() -> list[CriterionResult]:
    return [_criterion(criterion_id=cid, score=3) for cid in RUBRIC]


async def _persist_essay(
    database: Database,
    *,
    teacher_id: str = TEACHER_ID,
    class_id: str = CLASS_ID,
    run_id: str = RUN_ID,
    assignment_prompt: str = "Analyze the symbol.",
    essay_text: str = "essay text",
    student_name: str | None = None,
) -> uuid.UUID:
    return await database.persist_grading_run(
        run_id=run_id,
        teacher_id=teacher_id,
        class_id=class_id,
        assignment_prompt=assignment_prompt,
        student_name=student_name,
        essay_text=essay_text,
        segmentation_notes=None,
        s3_key=None,
        criteria=_all_fourteen_criteria(),
        model_version="claude-sonnet-5",
    )


@pytest.mark.asyncio
async def test_persist_grading_run_creates_a_session_essay_and_raw_grades(database):
    essay_id = await _persist_essay(database, student_name="Jane Doe")

    with database._session() as db:
        essay = db.get(Essay, essay_id)
        assert essay.student_name == "Jane Doe"
        assert essay.teacher_id == TEACHER_ID

        session_row = db.get(GradingSession, essay.session_id)
        assert session_row.class_id == CLASS_ID
        assert session_row.criteria_selection == {"full_essay": True}

        raw_grades = db.execute(select(RawGrade).where(RawGrade.essay_id == essay_id)).scalars().all()
        assert len(raw_grades) == 14
        assert all(r.run_id == RUN_ID for r in raw_grades)
        thesis_row = next(r for r in raw_grades if r.criterion_id == "thesis")
        assert thesis_row.source == "thesis"
        bp1_claim_row = next(r for r in raw_grades if r.criterion_id == "bp1-claim")
        assert bp1_claim_row.source == "body_1"
        conclusion_row = next(r for r in raw_grades if r.criterion_id == "conclusion")
        assert conclusion_row.source == "conclusion"


@pytest.mark.asyncio
async def test_persist_grading_run_reuses_the_session_for_the_same_teacher_class_and_prompt(database):
    essay_id_1 = await _persist_essay(database, essay_text="essay one")
    essay_id_2 = await _persist_essay(database, essay_text="essay two")

    with database._session() as db:
        session_id_1 = db.get(Essay, essay_id_1).session_id
        session_id_2 = db.get(Essay, essay_id_2).session_id
        assert session_id_1 == session_id_2


@pytest.mark.asyncio
async def test_persist_dispute_turn_creates_a_dispute_and_two_messages_with_no_proposal(database):
    essay_id = await _persist_essay(database)

    await database.persist_dispute_turn(
        essay_id=essay_id,
        caller_teacher_id=TEACHER_ID,
        criterion_id="bp1-evidence-1",
        teacher_message="I think this deserves a 3.",
        assistant_message="I'd stand by the 2 — the quote lacks context.",
        proposal=None,
        model_version="claude-sonnet-5",
    )

    with database._session() as db:
        dispute = db.execute(select(Dispute).where(Dispute.essay_id == essay_id)).scalar_one()
        assert dispute.status == "open"
        assert dispute.criterion_id == "bp1-evidence-1"
        # Pulled from the essay/session, not trusted from the request.
        assert dispute.teacher_id == TEACHER_ID
        assert dispute.class_id == CLASS_ID

        messages = (
            db.execute(select(DisputeMessageRow).where(DisputeMessageRow.dispute_id == dispute.id))
            .scalars()
            .all()
        )
        assert len(messages) == 2
        assert {m.role for m in messages} == {"teacher", "claude"}
        assert all(m.proposed_score is None and m.raw_grade_id is None for m in messages)


@pytest.mark.asyncio
async def test_persist_dispute_turn_raises_when_the_essay_doesnt_exist(database):
    with pytest.raises(EssayNotFoundError):
        await database.persist_dispute_turn(
            essay_id=uuid.uuid4(),
            caller_teacher_id=TEACHER_ID,
            criterion_id="bp1-evidence-1",
            teacher_message="hi",
            assistant_message="hi back",
            proposal=None,
            model_version="claude-sonnet-5",
        )


@pytest.mark.asyncio
async def test_persist_dispute_turn_raises_when_the_caller_doesnt_own_the_essay(database):
    essay_id = await _persist_essay(database, teacher_id=TEACHER_ID)

    with pytest.raises(EssayAccessDeniedError):
        await database.persist_dispute_turn(
            essay_id=essay_id,
            caller_teacher_id="a-different-teacher",
            criterion_id="bp1-evidence-1",
            teacher_message="hi",
            assistant_message="hi back",
            proposal=None,
            model_version="claude-sonnet-5",
        )


@pytest.mark.asyncio
async def test_persist_dispute_turn_writes_a_raw_grades_row_for_a_proposal_inheriting_run_id(database):
    essay_id = await _persist_essay(database)

    await database.persist_dispute_turn(
        essay_id=essay_id,
        caller_teacher_id=TEACHER_ID,
        criterion_id="bp1-evidence-1",
        teacher_message="Sentence 2 gives the context though.",
        assistant_message="Fair point — I'd revise this to a 3.",
        proposal=_criterion(score=3, sentence_refs=[1, 2]),
        model_version="claude-sonnet-5",
    )

    with database._session() as db:
        proposal_row = db.execute(
            select(RawGrade).where(RawGrade.essay_id == essay_id, RawGrade.source == "dispute-proposal")
        ).scalar_one()
        assert proposal_row.score == 3
        assert proposal_row.sentence_refs == [1, 2]
        # Inherited from the essay's original grading run, not independently generated.
        assert proposal_row.run_id == RUN_ID

        claude_message = db.execute(
            select(DisputeMessageRow).where(DisputeMessageRow.role == "claude")
        ).scalar_one()
        assert claude_message.proposed_score == 3
        assert claude_message.raw_grade_id == proposal_row.id


@pytest.mark.asyncio
async def test_persist_dispute_turn_reuses_the_same_open_dispute_across_turns(database):
    essay_id = await _persist_essay(database)
    turn_kwargs = {
        "essay_id": essay_id,
        "caller_teacher_id": TEACHER_ID,
        "criterion_id": "bp1-evidence-1",
        "model_version": "claude-sonnet-5",
    }

    await database.persist_dispute_turn(
        **turn_kwargs, teacher_message="msg 1", assistant_message="reply 1", proposal=None
    )
    await database.persist_dispute_turn(
        **turn_kwargs, teacher_message="msg 2", assistant_message="reply 2", proposal=None
    )

    with database._session() as db:
        disputes = db.execute(select(Dispute).where(Dispute.essay_id == essay_id)).scalars().all()
        assert len(disputes) == 1
        messages = (
            db.execute(select(DisputeMessageRow).where(DisputeMessageRow.dispute_id == disputes[0].id))
            .scalars()
            .all()
        )
        assert len(messages) == 4


@pytest.mark.asyncio
async def test_resolve_dispute_writes_accepted_grade_and_closes_the_dispute(database):
    essay_id = await _persist_essay(database)
    await database.persist_dispute_turn(
        essay_id=essay_id,
        caller_teacher_id=TEACHER_ID,
        criterion_id="bp1-evidence-1",
        teacher_message="Sentence 2 gives the context though.",
        assistant_message="Fair point — I'd revise this to a 3.",
        proposal=_criterion(score=3, sentence_refs=[1, 2]),
        model_version="claude-sonnet-5",
    )

    with database._session() as db:
        proposal_row = db.execute(
            select(RawGrade).where(RawGrade.essay_id == essay_id, RawGrade.source == "dispute-proposal")
        ).scalar_one()
        proposal_raw_grade_id = proposal_row.id

    accepted_grade_id, resolved_score, resolved_missing = await database.resolve_dispute(
        essay_id=essay_id,
        caller_teacher_id=TEACHER_ID,
        criterion_id="bp1-evidence-1",
        resolution="corrected",
        raw_grade_id=proposal_raw_grade_id,
    )
    assert resolved_score == 3
    assert resolved_missing is False

    with database._session() as db:
        accepted = db.get(AcceptedGrade, accepted_grade_id)
        assert accepted.score == 3
        assert accepted.raw_grade_id == proposal_raw_grade_id
        assert accepted.accepted_via == "dispute_save"

        dispute = db.execute(select(Dispute).where(Dispute.essay_id == essay_id)).scalar_one()
        assert dispute.status == "resolved"
        assert dispute.resolution == "corrected"
        assert dispute.accepted_grade_id == accepted_grade_id
        assert dispute.resolved_at is not None


@pytest.mark.asyncio
async def test_resolve_dispute_raises_when_there_is_no_open_dispute(database):
    essay_id = await _persist_essay(database)
    with pytest.raises(DisputeNotFoundError):
        await database.resolve_dispute(
            essay_id=essay_id,
            caller_teacher_id=TEACHER_ID,
            criterion_id="bp1-evidence-1",
            resolution="kept_original",
        )


@pytest.mark.asyncio
async def test_resolve_dispute_raises_when_the_essay_doesnt_exist(database):
    with pytest.raises(EssayNotFoundError):
        await database.resolve_dispute(
            essay_id=uuid.uuid4(),
            caller_teacher_id=TEACHER_ID,
            criterion_id="bp1-evidence-1",
            resolution="kept_original",
        )


@pytest.mark.asyncio
async def test_resolve_dispute_raises_when_the_caller_doesnt_own_the_essay(database):
    essay_id = await _persist_essay(database, teacher_id=TEACHER_ID)
    await database.persist_dispute_turn(
        essay_id=essay_id,
        caller_teacher_id=TEACHER_ID,
        criterion_id="bp1-evidence-1",
        teacher_message="I think this deserves a 4.",
        assistant_message="I'd stand by the original score.",
        proposal=None,
        model_version="claude-sonnet-5",
    )

    with pytest.raises(EssayAccessDeniedError):
        await database.resolve_dispute(
            essay_id=essay_id,
            caller_teacher_id="a-different-teacher",
            criterion_id="bp1-evidence-1",
            resolution="kept_original",
        )


@pytest.mark.asyncio
async def test_resolve_dispute_kept_original_points_at_the_original_grade(database):
    essay_id = await _persist_essay(database)
    await database.persist_dispute_turn(
        essay_id=essay_id,
        caller_teacher_id=TEACHER_ID,
        criterion_id="bp1-evidence-1",
        teacher_message="I think this deserves a 4.",
        assistant_message="I'd stand by the original score.",
        proposal=None,
        model_version="claude-sonnet-5",
    )

    accepted_grade_id, resolved_score, resolved_missing = await database.resolve_dispute(
        essay_id=essay_id,
        caller_teacher_id=TEACHER_ID,
        criterion_id="bp1-evidence-1",
        resolution="kept_original",
    )

    assert resolved_score == 3  # the original raw_grades row's score, from _all_fourteen_criteria()
    assert resolved_missing is False

    with database._session() as db:
        accepted = db.get(AcceptedGrade, accepted_grade_id)
        original_row = db.execute(
            select(RawGrade).where(
                RawGrade.essay_id == essay_id,
                RawGrade.criterion_id == "bp1-evidence-1",
                RawGrade.source == "body_1",
            )
        ).scalar_one()
        assert accepted.raw_grade_id == original_row.id


@pytest.mark.asyncio
async def test_resolve_dispute_rejects_a_raw_grade_id_from_a_different_essay(database):
    essay_id_1 = await _persist_essay(database, essay_text="essay one")
    essay_id_2 = await _persist_essay(database, assignment_prompt="A different prompt.", essay_text="essay two")
    await database.persist_dispute_turn(
        essay_id=essay_id_1,
        caller_teacher_id=TEACHER_ID,
        criterion_id="bp1-evidence-1",
        teacher_message="msg",
        assistant_message="reply",
        proposal=None,
        model_version="claude-sonnet-5",
    )

    with database._session() as db:
        other_essays_raw_grade = db.execute(
            select(RawGrade).where(
                RawGrade.essay_id == essay_id_2, RawGrade.criterion_id == "bp1-evidence-1"
            )
        ).scalar_one()
        mismatched_id = other_essays_raw_grade.id

    with pytest.raises(RawGradeMismatchError):
        await database.resolve_dispute(
            essay_id=essay_id_1,
            caller_teacher_id=TEACHER_ID,
            criterion_id="bp1-evidence-1",
            resolution="corrected",
            raw_grade_id=mismatched_id,
        )


@pytest.mark.asyncio
async def test_a_missing_proposal_still_gets_a_raw_grade_row_despite_a_null_score(database):
    essay_id = await _persist_essay(database)

    await database.persist_dispute_turn(
        essay_id=essay_id,
        caller_teacher_id=TEACHER_ID,
        criterion_id="bp1-evidence-1",
        teacher_message="Actually there's nothing here at all.",
        assistant_message="You're right — nothing in the essay addresses this.",
        proposal=CriterionResult(
            criterion_id="bp1-evidence-1",
            score=None,
            missing=True,
            strengths=[],
            critiques=["Nothing addresses this criterion."],
            reasoning="No sentence attempts evidence here.",
            sentence_refs=[],
        ),
        model_version="claude-sonnet-5",
    )

    with database._session() as db:
        proposal_row = db.execute(
            select(RawGrade).where(RawGrade.essay_id == essay_id, RawGrade.source == "dispute-proposal")
        ).scalar_one()
        assert proposal_row.score is None
        assert proposal_row.missing is True

        claude_message = db.execute(
            select(DisputeMessageRow).where(DisputeMessageRow.role == "claude")
        ).scalar_one()
        assert claude_message.proposed_score is None
        assert claude_message.raw_grade_id == proposal_row.id
