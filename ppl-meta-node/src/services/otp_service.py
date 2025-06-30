import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.otp import OTP

def generate_otp_code() -> str:
    return f"{random.randint(100000, 999999)}"

def create_otp(db: Session, user_id: int, expires_in_minutes: int = 5) -> OTP:
    code = generate_otp_code()
    expires_at = datetime.now() + timedelta(minutes=expires_in_minutes)
    otp = OTP(user_id=user_id, code=code, expires_at=expires_at)
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return otp

def verify_otp(db: Session, user_id: int, code: str) -> bool:
    otp = (
        db.query(OTP)
        .filter(
            OTP.user_id == user_id,
            OTP.code == code,
            OTP.expires_at > datetime.now(),
            OTP.used == False
        )
        .order_by(OTP.created_at.desc())
        .first()
    )
    if otp:
        otp.used = True
        db.commit()
        return True
    return False