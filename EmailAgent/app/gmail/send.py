import base64
import mimetypes
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def send_email(
    service,
    to,
    subject,
    body,
    approval_status,
    cc=None,
    bcc=None,
    attachments=None,
    thread_id=None,
    in_reply_to=None,
    references=None,
):
    if approval_status != "APPROVED":
        raise PermissionError("Email send blocked: approval required")

    def normalize_header(value):
        if not value:
            return None
        if isinstance(value, list):
            return ", ".join(value)
        if isinstance(value, str):
            return value
        raise TypeError(f"Invalid header type: {type(value)}")

    if attachments:
        message = MIMEMultipart()
        message.attach(MIMEText(body, "plain"))
    else:
        message = MIMEText(body, "plain")

    message["To"] = normalize_header(to)
    message["Subject"] = subject or ""
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to

    if references:
        message["References"] = references


    cc_header = normalize_header(cc)
    bcc_header = normalize_header(bcc)

    if cc_header:
        message["Cc"] = cc_header
    if bcc_header:
        message["Bcc"] = bcc_header

    for file_path in attachments or []:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Attachment not found: {file_path}")

        content_type, encoding = mimetypes.guess_type(file_path)
        if content_type is None or encoding is not None:
            content_type = "application/octet-stream"

        main_type, sub_type = content_type.split("/", 1)

        with open(file_path, "rb") as f:
            part = MIMEBase(main_type, sub_type)
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{os.path.basename(file_path)}"',
        )
        message.attach(part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    body_payload = {"raw": raw}

    if thread_id and (in_reply_to or references):
        body_payload["threadId"] = thread_id

    service.users().messages().send(
        userId="me",
        body=body_payload
    ).execute()

