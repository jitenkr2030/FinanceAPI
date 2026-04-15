from sqlalchemy.orm import Session
from app.models.report import Report

def create_report(db: Session, user_id: int, report_type: str, file_path: str = None):
    report = Report(
        user_id=user_id,
        report_type=report_type,
        file_path=file_path
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report
