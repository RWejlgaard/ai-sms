"""
This module provides functions for managing conversations in the database.
"""

import sqlite3
import json
import os

# if conversations.sqlite does not exist when started, create it
if not os.path.exists('conversations.sqlite'):
    conn = sqlite3.connect('conversations.sqlite')
    c = conn.cursor()
    c.execute('CREATE TABLE conversations (phoneno TEXT PRIMARY KEY, messages TEXT)')
    conn.commit()
    conn.close()


def get_conversations():
    """
    Returns a list of all conversations in the database
    return: list(dict)
    """
    conn = sqlite3.connect('conversations.sqlite')
    c = conn.cursor()
    c.execute('SELECT * FROM conversations')
    conversations = c.fetchall()
    conn.close()
    return conversations

def set_default_messages(phone_number, system_message="you're a helpful assistant. Your messages are text messages. Be consise"):
    """
    Sets the default messages for a phone number
    phone_number: str
    system_message: str
    """
    messages = [
        {"role": "system", "content": system_message},
    ]

    if get_messages(phone_number): # if messages already exist, delete them
        delete_messages(phone_number)

    conn = sqlite3.connect('conversations.sqlite')
    c = conn.cursor()
    c.execute('INSERT INTO conversations (phoneno, messages) VALUES (?, ?)', (phone_number, json.dumps(messages)))
    conn.commit()
    conn.close()


def get_messages(phone_number):
    """
    Returns the messages for a phone number from the database
    phone_number: str
    return: list(dict)
    """
    conn = sqlite3.connect('conversations.sqlite')
    c = conn.cursor()
    c.execute('SELECT messages FROM conversations WHERE phoneno = ?', (phone_number,))
    messages = c.fetchone()
    conn.close()
    return json.loads(messages[0]) if messages else None

def add_message(phone_number, message, role):
    """
    Adds a message to the conversation history for a phone number, and returns the updated conversation history.
    if the phone number does not exist, it will be created with a default system message
    phone_number: str
    message: str
    role: str
    return: list(dict)
    """
    messages = get_messages(phone_number)
    if not messages:
        set_default_messages(phone_number)
        messages = get_messages(phone_number)

    messages.append({"role": role, "content": message})

    conn = sqlite3.connect('conversations.sqlite')
    c = conn.cursor()
    c.execute('UPDATE conversations SET messages = ? WHERE phoneno = ?', (json.dumps(messages), phone_number))
    conn.commit()
    conn.close()

    return messages

def delete_messages(phone_number):
    """
    Deletes the messages for a phone number from the database
    phone_number: str
    """
    conn = sqlite3.connect('conversations.sqlite')
    c = conn.cursor()
    c.execute('DELETE FROM conversations WHERE phoneno = ?', (phone_number,))
    conn.commit()
    conn.close()