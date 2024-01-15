from django.contrib.auth import authenticate, login, logout #new
from django.shortcuts import render, redirect #new
from django.http import HttpResponse
from django.shortcuts import render
from premailer import transform

import smtplib
import ssl
import base64
import os
from email.message import EmailMessage
from os.path import basename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from django.shortcuts import render
from django.http import HttpResponse
import imaplib
import email
from email.header import decode_header
from django.contrib import messages


def compose_email(request):
    if request.method == 'POST':
        receiver_email = request.POST.get('receiver')
        cc_email = request.POST.get('cc', '')  # Optional field, default to empty string if not provided
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        attachment = request.FILES.get('attachment')
        sender_email = request.session.get('user_email')
        # Now you can use the form data as needed, such as sending an email or saving it to the database

        # For now, let's just print the data to the console
        print(f"Sender: {sender_email}")
        print(f"Receiver: {receiver_email}")
        print(f"CC: {cc_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")

        # determine the folder the python file is located in
        curr_folder = os.path.dirname(os.path.abspath(__file__))

        # specify the email address of the sender of the email
        email_sender = sender_email

        # specify the generated app password used for authentication when the program logs in to the gmail server
        # password was changed to hide my app_password for submission purposes
        app_password = request.session.get('app_password')

        # Check if the app password is available in the session
        if not app_password:
            # Handle the case where the app password is not found
            return HttpResponse("App password not found. Please log in.")

        # specify the email address of the original receiver and any other email addresses to be forwarded to
        email_receiver = receiver_email
        email_cc_receivers = [cc_email]

        # combine the above email addresses into a list of addresses for the email to be sent to
        full_recipients = [email_receiver] + email_cc_receivers

        # define the subject line of the email and the content body
        email_subject = subject
        email_body = body

        # build the email message to be sent including the information to be displayed in the email's header
        # (CC information, To, From, etc)
        em = MIMEMultipart()
        em['From'] = email_sender
        em['To'] = email_receiver
        em['CC'] = ', '.join(email_cc_receivers)
        em['Subject'] = email_subject
        em.attach(MIMEText(email_body, 'plain'))
        if attachment:
            em.attach(MIMEApplication(attachment.read(), Name=attachment.name))
            em['Content-Disposition'] = f'attachment; filename="{attachment.name}"'

        # context used to establish connection with Gmail's SMTP server
        context = ssl.create_default_context()

        # establish the SMTP connection to the Gmail server and undergo the transaction process
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_sender, app_password)
            smtp.sendmail(email_sender, full_recipients, em.as_string())
            smtp.quit()

        # Add your email sending or database saving logic here
        messages.success(request, 'Email sent successfully!')

        return redirect('inbox', user_email=email_sender, app_password=app_password)

    return render(request, 'compose_email.html')


# Function to display the inbox and retrieve email information
def display_inbox(request, user_email, app_password):
    # IMAP server and port configuration
    imap_server = "imap.gmail.com"
    imap_port = 993

    # Establish an SSL connection to the IMAP server
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(user_email, app_password)
    mail.select("inbox")

    # Retrieve email IDs of the latest 10 emails in the inbox
    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split()[::-1][:10]

    emails = []

    # Iterate through each email ID to fetch email details
    for email_id in email_ids:
        _, msg_data = mail.fetch(email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")

        from_address = msg.get("From")
        date = msg.get("Date")

        # Extract email body from multipart or plain text format
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    emails.append({"subject": subject, "from": from_address, "date": date})
                    break
        else:
            body = msg.get_payload(decode=True)
            emails.append({"subject": subject, "from": from_address, "date": date})
    mail.logout()

    # Prepare context for rendering the inbox template
    context = {'emails': emails}
    return render(request, 'inbox.html', context)


# Function to retrieve email details by ID
def get_email_by_id(user_email, app_password, email_id):
    # IMAP server and port configuration
    imap_server = "imap.gmail.com"
    imap_port = 993

    # Establish an SSL connection to the IMAP server
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(user_email, app_password)
    mail.select("inbox")

    # Retrieve the email based on the provided email_id
    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split()[::-1][:10]

    selected_email_id = email_ids[email_id - 1]  # Adjust index to start from 0
    _, msg_data = mail.fetch(selected_email_id, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])

    # Extract email information
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8")

    from_address = msg.get("From")
    date = msg.get("Date")
    body = None

    # Extract email body from multipart or plain text format
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                body = transform(body)  # Assuming 'transform' is a defined function
                break
            elif part.get_content_type() == "text/plain" and body is None:
                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                body = transform(body)  # Assuming 'transform' is a defined function
    else:
        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        body = transform(body)  # Assuming 'transform' is a defined function

    # Logout from the email server
    mail.logout()

    # Return the email information as a dictionary
    return {
        'id': email_id,
        'subject': subject,
        'from': from_address,
        'date': date,
        'body': body,
    }


# Function to handle replying to an email
def reply_email(request, email_id):
    # Retrieve the original email information using the identifier (email_id)
    original_email_info = get_email_by_id(request.session['user_email'], request.session['app_password'], int(email_id))

    if not original_email_info:
        # Handle the case where the original email is not found
        return render(request, 'email_not_found.html')

    sender_email = request.session.get('user_email')
    receiver_email = original_email_info['from']
    print(receiver_email)

    if request.method == 'POST':
        # Retrieve form inputs for email reply
        cc_email = request.POST.get('cc', '')  # Optional field, default to empty string if not provided
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        attachment = request.FILES.get('attachment')

        # Send the email reply using SMTP and Gmail server
        email_receiver = receiver_email
        email_cc_receivers = [cc_email]

        # Build the email message to be sent, including header information
        em = MIMEMultipart()
        em['From'] = sender_email
        em['To'] = receiver_email
        em['CC'] = ', '.join(email_cc_receivers)
        em['Subject'] = subject
        em.attach(MIMEText(body, 'plain'))
        if attachment:
            em.attach(MIMEApplication(attachment.read(), Name=attachment.name))
            em['Content-Disposition'] = f'attachment; filename="{attachment.name}"'

        # Context used to establish connection with Gmail's SMTP server
        context = ssl.create_default_context()
        full_recipients = [email_receiver] + email_cc_receivers
        # Establish the SMTP connection to the Gmail server and send the email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(sender_email, request.session['app_password'])
            smtp.sendmail(sender_email, full_recipients, em.as_string())
            smtp.quit()

        return redirect('inbox', user_email=request.session['user_email'], app_password=request.session['app_password'])

    # Pre-fill the reply form with the original email information
    initial_data = {
        'receiver': receiver_email,
        'subject': f"Re: {original_email_info['subject']}",
        'body': f"\n\n\n------ Original Message ------\nFrom: {original_email_info['from']}\nDate: {original_email_info['date']}\nSubject: {original_email_info['subject']}\n\n{original_email_info['body']}",
    }

    return render(request, 'reply_email.html', {'initial_data': initial_data})


# Function to display detailed information about an email
def email_detail(request, email_id):
    # Retrieve the email information using the identifier (email_id)
    email_info = get_email_by_id(request.session['user_email'], request.session['app_password'], int(email_id))

    if not email_info:
        # Handle the case where the email is not found
        return render(request, 'email_not_found.html')

    # Render the email_detail.html template with the email information
    return render(request, 'email_detail.html', {'email': email_info})


# Function to handle user login
def login(request):
    if request.method == 'POST':
        # Retrieve user inputs from the login form
        user_email = request.POST.get('email')
        app_password = request.POST.get('app_password')

        # Use the provided email and app password for authentication
        context = display_inbox(request, user_email, app_password)

        if context:
            # Store the email and app password in the session for future use
            request.session['user_email'] = user_email
            request.session['app_password'] = app_password

            # Redirect to the inbox with the provided user_email and app_password
            return redirect('inbox', user_email=user_email, app_password=app_password)
        else:
            return render(request, 'login.html', {'error_message': "Authentication failed. Please check your credentials."})

    return render(request, 'login.html')

