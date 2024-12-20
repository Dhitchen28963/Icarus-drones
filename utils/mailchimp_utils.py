import requests
from django.conf import settings


class Mailchimp:
    """Utility class for interacting with the Mailchimp API"""

    def __init__(self):
        self.api_key = settings.MAILCHIMP_API_KEY
        self.server_prefix = settings.MAILCHIMP_SERVER_PREFIX
        self.audience_id = settings.MAILCHIMP_AUDIENCE_ID
        self.base_url = f"https://{self.server_prefix}.api.mailchimp.com/3.0"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def subscribe_user(self, email, first_name='', last_name='',
                       tags=None, address=None):
        """
        Add or update a user subscription in the Mailchimp audience.
        If the user already exists, their information will be updated.

        Args:
            email (str): The user's email address.
            first_name (str): The user's first name (optional).
            last_name (str): The user's last name (optional).
            tags (list): Tags to associate with the user (optional).
            address (dict): Address details (optional). Format:
                            {'addr1': '123 Street Name', 'city': 'City',
                            'state': 'State', 'zip': '12345', 'country': 'US'}
        """
        url = f"{self.base_url}/lists/{self.audience_id}/members"
        subscriber_hash = self._get_subscriber_hash(email)
        data = {
            "email_address": email,
            "status_if_new": "subscribed",
            "merge_fields": {
                "FNAME": first_name,
                "LNAME": last_name,
                "ADDRESS": {
                    "addr1": address.get("addr1", ""),
                    "city": address.get("city", ""),
                    "state": address.get("state", ""),
                    "zip": address.get("zip", ""),
                    "country": address.get("country", ""),
                },
            },
        }

        if tags:
            data["tags"] = tags

        response = requests.put(f"{url}/{subscriber_hash}", json=data,
                                headers=self.headers)
        if response.status_code not in (200, 204):
            raise Exception(
                f"Mailchimp API error: {response.status_code} {response.text}")
        return response.json()

    def add_tags_to_user(self, email, tags):
        """
        Add tags to an existing subscriber in the Mailchimp audience.

        Args:
            email (str): The user's email address.
            tags (list): List of tags to add.

        Returns:
            dict: API response from Mailchimp.
        """
        url = (f"{self.base_url}/lists/{self.audience_id}/members/"
               f"{self._get_subscriber_hash(email)}/tags")
        data = {
            "tags": [{"name": tag, "status": "active"} for tag in tags]
        }

        response = requests.post(url, json=data, headers=self.headers)
        if response.status_code != 200:
            raise Exception(
                f"Mailchimp API error: {response.status_code} {response.text}")
        return response.json()

    def remove_tags_from_user(self, email, tags):
        """
        Remove tags from an existing subscriber in the Mailchimp audience.

        Args:
            email (str): The user's email address.
            tags (list): List of tags to remove.

        Returns:
            dict: API response from Mailchimp.
        """
        url = (f"{self.base_url}/lists/{self.audience_id}/members/"
               f"{self._get_subscriber_hash(email)}/tags")
        data = {
            "tags": [{"name": tag, "status": "inactive"} for tag in tags]
        }

        response = requests.post(url, json=data, headers=self.headers)
        if response.status_code != 200:
            raise Exception(
                f"Mailchimp API error: {response.status_code} {response.text}")
        return response.json()

    def _get_subscriber_hash(self, email):
        """
        Generate the MD5 hash of the user's email address as required
        by Mailchimp API.

        Args:
            email (str): The user's email address.

        Returns:
            str: MD5 hash of the email address.
        """
        import hashlib
        return hashlib.md5(email.lower().encode()).hexdigest()
