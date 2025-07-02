from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.schemas.otp import OTPCreate
from src.database import get_db
from src.services.user_service import get_user_by_id, log_user_action
from src.mail import send_email
from src.services.otp_service import create_otp, verify_otp
from src.auth_utils import create_access_token


router = APIRouter(prefix="/otp", tags=["otp"])


@router.post("/send")
async def send_otp(data: OTPCreate, db: Session = Depends(get_db)):
    user = get_user_by_id(db, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    otp = create_otp(db, user.id)
    email_body = f"Your OTP code is: <b>{otp.code}</b>. It expires in 5 minutes."
    await send_email(
        subject="Your OTP Code",
        email_to=user.email,
        body=email_body
    )
    return {"detail": "OTP sent to your email."}

@router.post("/verify-otp")
async def verify_otp_api(email: str, otp_code: str, db: Session = Depends(get_db)):
    user = get_user_by_id(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Assume you have a function to verify the OTP code
    if not verify_otp(db, user, otp_code):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code")
    log_user_action(db, user.username, user.email, "otp_verified")
    # Generate access token after successful OTP verification
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}