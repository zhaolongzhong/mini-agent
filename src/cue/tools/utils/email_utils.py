import base64
import logging
import os.path
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]


def get_user_credential():
    token_path = "credentials/token_gmail.json"
    credentials_path = "credentials/credentials.json"
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        logger.debug(f"token exists, valid: {creds.valid}")
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        logger.debug(f"token not exists or not valid: {creds}")
        logger.debug(f"token not exists or not valid: {creds}")
        if creds:
            logger.debug(f"token expired: {creds.expired}, valid:{creds.valid}")
        if creds and creds.expired and creds.refresh_token:
            logger.debug("refres token...")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        # Store in database in production
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return creds


def get_service():
    creds = get_user_credential()
    if not creds:
        logger.error("No credentials")
        return "No credentials"
    return build("gmail", "v1", credentials=creds)


def get_user_email(service):
    """Gets the email address of the authenticated user."""
    user_info_service = build("oauth2", "v2", credentials=service._http.credentials)
    user_info = user_info_service.userinfo().get().execute()
    return user_info.get("email")


def read_email(max_count: str = 10) -> list[dict]:
    """Shows basic usage of the Gmail API.
    Lists the subject lines of the last 10 emails in the user's inbox.
    """
    service = get_service()
    results = service.users().messages().list(userId="me", maxResults=max_count).execute()
    messages = results.get("messages", [])

    results = []
    if not messages:
        logger.error("No messages found.")
        return ["No messages found."]
    else:
        for message in messages:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
            results.append(
                {
                    "id": msg["id"],
                    "snippet": msg["snippet"],
                }
            )
    logger.debug(f"read_email: {len(results)}")
    return results


def get_email_details(message_id) -> dict:
    """Get detailed information about an email message."""
    service = get_service()
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    email_data = {
        "id": message.get("id"),
        "threadId": message.get("threadId"),
        "snippet": message.get("snippet"),
        "labelIds": message.get("labelIds"),
    }

    for header in headers:
        name = header.get("name")
        value = header.get("value")
        if name.lower() == "from":
            email_data["from"] = value
        elif name.lower() == "to":
            email_data["to"] = value
        elif name.lower() == "subject":
            email_data["subject"] = value
        elif name.lower() == "date":
            email_data["date"] = value

    parts = payload.get("parts", [])
    email_data["body"] = ""

    for part in parts:
        if part.get("mimeType") == "text/plain":
            body = part.get("body", {}).get("data")
            if body:
                email_data["body"] = base64.urlsafe_b64decode(body).decode("utf-8")

    return email_data


def _create_message(to, subject, message_text):
    message = MIMEText(message_text)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_message(service, user_id, message) -> str:
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        return "Sent to {} successfully, message id: {}".format(user_id, message["id"])
    except Exception as error:
        logger.error(f"An error occurred: {error}")
        return f"An error occurred: {error}"


def send_email(to_email: str, subject: str, content: str) -> str:
    """Shows basic usage of the Gmail API.
    Sends an email.
    """
    service = get_service()
    message = _create_message(to_email, subject, content)
    return send_message(service, "me", message)


def main():
    res = read_email(max_count=2)
    print(res)
    detail_res = get_email_details(get_service(), res[1]["id"])
    print(detail_res)
    # send_email()


if __name__ == "__main__":
    main()
