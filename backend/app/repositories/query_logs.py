from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.conversation import Message
from app.models.query_log import QueryLog


class QueryLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, log: QueryLog) -> QueryLog:
        self.db.add(log)
        self.db.flush()
        return log

    def stats(self) -> dict:
        row = self.db.execute(
            select(
                func.count(QueryLog.id),
                func.avg(case((QueryLog.answered, 1.0), else_=0.0)),
                func.avg(QueryLog.retrieval_ms),
                func.avg(QueryLog.total_ms),
                func.percentile_cont(0.95).within_group(QueryLog.total_ms),
                func.count(QueryLog.error),
            )
        ).one()
        feedback = dict(
            self.db.execute(
                select(Message.feedback, func.count())
                .where(Message.feedback.is_not(None))
                .group_by(Message.feedback)
            ).all()
        )
        total, answer_rate, avg_retrieval, avg_total, p95_total, errors = row
        return {
            "total": total,
            "answer_rate": round(float(answer_rate), 3) if answer_rate is not None else None,
            "avg_retrieval_ms": round(float(avg_retrieval)) if avg_retrieval is not None else None,
            "avg_total_ms": round(float(avg_total)) if avg_total is not None else None,
            "p95_total_ms": round(float(p95_total)) if p95_total is not None else None,
            "errors": errors,
            "feedback_up": feedback.get(1, 0),
            "feedback_down": feedback.get(-1, 0),
        }
