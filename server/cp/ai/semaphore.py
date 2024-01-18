import os
import logging
import requests
import xml.etree.ElementTree as ET
from flask import current_app, abort
from superdesk.text_checkers.ai.base import AIServiceBase
import traceback
import json


logger = logging.getLogger(__name__)
session = requests.Session()

TIMEOUT = (5, 30)


class Semaphore(AIServiceBase):
    """Semaphore autotagging service

    Environment variables SEMAPHORE_BASE_URL, SEMAPHORE_ANALYZE_URL, SEMAPHORE_SEARCH_URL, SEMAPHORE_GET_PARENT_URL
    and SEMAPHORE_API_KEY must be set.
    """

    name = "semaphore"
    label = "Semaphore autotagging service"

    def __init__(self, app=None):
        # SEMAPHORE_BASE_URL OR TOKEN_ENDPOINT Goes Here
        self.base_url = os.getenv("SEMAPHORE_BASE_URL")

        #  SEMAPHORE_ANALYZE_URL Goes Here
        self.analyze_url = os.getenv("SEMAPHORE_ANALYZE_URL")

        #  SEMAPHORE_API_KEY Goes Here
        self.api_key = os.getenv("SEMAPHORE_API_KEY")

        #  SEMAPHORE_SEARCH_URL Goes Here
        self.search_url = os.getenv("SEMAPHORE_SEARCH_URL")

        #  SEMAPHORE_GET_PARENT_URL Goes Here
        self.get_parent_url = os.getenv("SEMAPHORE_GET_PARENT_URL")

    def convert_to_desired_format(input_data):
        result = {
            "result": {
                "tags": {
                    "subject": input_data["subject"],
                    "organisation": input_data["organisation"],
                    "person": input_data["person"],
                    "event": input_data["event"],
                    "place": input_data["place"],
                    "object": [],  # Assuming no data for 'object'
                },
                "broader": {"subject": input_data["broader"]},
            }
        }

        return result

    def get_access_token(self):
        """Get access token for Semaphore."""
        url = self.base_url

        payload = f"grant_type=apikey&key={self.api_key}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = session.post(url, headers=headers, data=payload, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json().get("access_token")

    def fetch_parent_info(self, qcode):
        headers = {"Authorization": f"Bearer {self.get_access_token()}"}
        try:
            frank = "?relationshipType=has%20broader"

            query = qcode
            parent_url = self.get_parent_url + query + frank

            response = session.get(parent_url, headers=headers)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            path = root.find(".//PATH[@TYPE='Narrower Term']")
            parent_info = []
            if path is not None:
                for field in path.findall("FIELD"):
                    if field.find("CLASS").get("NAME") == "Topic":
                        parent_info.append(
                            {
                                "name": field.get("NAME"),
                                "qcode": field.get("ID"),
                                "parent": None,  # Set to None initially
                            }
                        )
            return parent_info, parent_info[::-1]

        except Exception as e:
            logger.error(f"Error fetching parent info: {str(e)}")
            return []

    def analyze_2(self, html_content: str) -> dict:
        try:
            if not self.base_url or not self.api_key:
                logger.warning(
                    "Semaphore Search is not configured properly, can't analyze content"
                )
                return {}

            query = html_content["searchString"]

            new_url = self.search_url + query + ".json"

            # Make a POST request using XML payload
            headers = {"Authorization": f"bearer {self.get_access_token()}"}

            try:
                response = session.get(new_url, headers=headers)

                response.raise_for_status()
            except Exception as e:
                traceback.print_exc()
                logger.error(f"An error occurred while making the request: {str(e)}")

            root = response.text

            # def transform_xml_response(xml_data):
            def transform_xml_response(api_response):
                result = {
                    "subject": [],
                    "organisation": [],
                    "person": [],
                    "event": [],
                    "place": [],
                    "broader": [],
                }

                # Process each termHint item in the API response
                for item in api_response["termHints"]:
                    scheme_url = "http://cv.cp.org/"

                    if "Organization" in item["classes"]:
                        scheme_url = "http://cv.cp.org/Organizations/"
                        category = "organisation"
                    elif "People" in item["classes"]:
                        scheme_url = "http://cv.cp.org/People/"
                        category = "person"
                    elif "Event" in item["classes"]:
                        scheme_url = "http://cv.cp.org/Events/"
                        category = "event"
                    elif "Place" in item["classes"]:
                        scheme_url = "http://cv.cp.org/Places/"
                        category = "place"
                    else:
                        # For 'subject', a different scheme might be used
                        category = "subject"
                        scheme_url = "http://cv.iptc.org/newscodes/mediatopic/"

                    entry = {
                        "name": item["name"],
                        "qcode": item["id"],
                        "source": "Semaphore",
                        "altids": {"source_name": "source_id"},
                        "original_source": "original_source_value",
                        "scheme": scheme_url,
                        "parent": None,  # Initial parent assignment
                    }

                    # Assign to correct category based on class
                    if "Organization" in item["classes"]:
                        result["organisation"].append(entry)
                    elif "People" in item["classes"]:
                        result["person"].append(entry)
                    elif "Event" in item["classes"]:
                        result["event"].append(entry)
                    elif "Place" in item["classes"]:
                        result["place"].append(entry)
                    else:
                        # Fetch parent info for each subject item
                        parent_info, reversed_parent_info = self.fetch_parent_info(
                            item["id"]
                        )

                        # Assign the immediate parent to the subject item
                        if parent_info:
                            entry["parent"] = reversed_parent_info[0][
                                "qcode"
                            ]  # Immediate parent is the first in the list
                            entry["scheme"] = "http://cv.iptc.org/newscodes/mediatopic/"

                        result["subject"].append(entry)

                        # Process broader items using reversed_parent_info
                        for i in range(len(reversed_parent_info)):
                            broader_entry = {
                                "name": reversed_parent_info[i]["name"],
                                "qcode": reversed_parent_info[i]["qcode"],
                                "parent": reversed_parent_info[i + 1]["qcode"]
                                if i + 1 < len(reversed_parent_info)
                                else None,
                                "source": "Semaphore",
                                "altids": {"source_name": "source_id"},
                                "original_source": "original_source_value",
                                "scheme": "http://cv.iptc.org/newscodes/mediatopic/",
                            }
                            result["broader"].append(broader_entry)

                return result

            def convert_to_desired_format(input_data):
                result = {
                    "result": {
                        "tags": {
                            "subject": input_data["subject"],
                            "organisation": input_data["organisation"],
                            "person": input_data["person"],
                            "event": input_data["event"],
                            "place": input_data["place"],
                            "object": [],  # Assuming no data for 'object'
                        },
                        "broader": {"subject": input_data["broader"]},
                    }
                }

                return result

            root = json.loads(root)
            json_response = transform_xml_response(root)

            json_response = convert_to_desired_format(json_response)

            return json_response

        except requests.exceptions.RequestException as e:
            traceback.print_exc()
            logger.error(
                f"Semaphore Search request failed. We are in analyze RequestError exception: {str(e)}"
            )

    def analyze(self, html_content: str, tags=None) -> dict:
        try:
            if not self.base_url or not self.api_key:
                logger.warning(
                    "Semaphore is not configured properly, can't analyze content"
                )
                return {}

            try:
                for key, value in html_content.items():
                    if key == "searchString":
                        print(
                            "______________________________________---------------------------------------"
                        )
                        print("Running for Search")

                        self.output = self.analyze_2(html_content)
                        return self.output

            except TypeError:
                pass

            # Convert HTML to XML
            xml_payload = self.html_to_xml(html_content)

            payload = {"XML_INPUT": xml_payload}

            # Make a POST request using XML payload
            headers = {"Authorization": f"bearer {self.get_access_token()}"}

            logger.info(
                "REQUEST url=%s headers=%s payload=%s",
                self.analyze_url,
                headers,
                payload,
            )

            try:
                response = session.post(self.analyze_url, headers=headers, data=payload)
                response.raise_for_status()
            except Exception as e:
                traceback.print_exc()
                logger.error(f"An error occurred while making the request: {str(e)}")

            root = response.text

            def transform_xml_response(xml_data):
                # Parse the XML data
                root = ET.fromstring(xml_data)

                # Initialize a dictionary to hold the transformed data
                response_dict = {
                    "subject": [],
                    "organisation": [],
                    "person": [],
                    "event": [],
                    "place": [],
                }

                # Temporary storage for path labels and GUIDs
                path_labels = {}
                path_guids = {}

                # Helper function to add data to the dictionary if it's not a duplicate and has a qcode
                def add_to_dict(group, tag_data):
                    if tag_data["qcode"] and tag_data not in response_dict[group]:
                        response_dict[group].append(tag_data)

                # Iterate through the XML elements and populate the dictionary
                for element in root.iter():
                    if element.tag == "META":
                        meta_name = element.get("name")
                        meta_value = element.get("value")
                        meta_score = element.get("score")
                        meta_id = element.get("id")

                        # Process 'Media Topic_PATH_LABEL' and 'Media Topic_PATH_GUID'
                        if meta_name == "Media Topic_PATH_LABEL":
                            path_labels[meta_score] = meta_value.split("/")[1:]
                        elif meta_name == "Media Topic_PATH_GUID":
                            path_guids[meta_score] = meta_value.split("/")[1:]

                        # Process other categories
                        else:
                            group = None
                            if "Organization" in meta_name:
                                group = "organisation"
                                scheme_url = "http://cv.cp.org/Organizations/"
                            elif "Person" in meta_name:
                                group = "person"
                                scheme_url = "http://cv.cp.org/People/"
                            elif "Event" in meta_name:
                                group = "event"
                                scheme_url = "http://cv.cp.org/Events/"
                            elif "Place" in meta_name:
                                group = "place"
                                scheme_url = "http://cv.cp.org/Places/"

                            if group:
                                tag_data = {
                                    "name": meta_value,
                                    "qcode": meta_id if meta_id else "",
                                    "source": "Semaphore",
                                    "altids": {"source_name": "source_id"},
                                    "original_source": "original_source_value",
                                    "scheme": scheme_url,
                                }
                                add_to_dict(group, tag_data)

                # Match path labels with path GUIDs based on scores
                for score, labels in path_labels.items():
                    guids = path_guids.get(score, [])
                    if len(labels) != len(guids):
                        continue  # Skip if there's a mismatch in the number of labels and GUIDs

                    parent_qcode = None  # Track the parent qcode
                    for label, guid in zip(labels, guids):
                        tag_data = {
                            "name": label,
                            "qcode": guid,
                            "parent": parent_qcode,
                            "source": "Semaphore",
                            "altids": {"source_name": "source_id"},
                            "original_source": "original_source_value",
                            "scheme": "http://cv.iptc.org/newscodes/mediatopic/",
                        }
                        add_to_dict("subject", tag_data)
                        parent_qcode = (
                            guid  # Update the parent qcode for the next iteration
                        )

                return response_dict

            json_response = transform_xml_response(root)

            return json_response

        except requests.exceptions.RequestException as e:
            traceback.print_exc()
            logger.error(
                f"Semaphore request failed. We are in analyze RequestError exception: {str(e)}"
            )

        except Exception as e:
            traceback.print_exc()
            logger.error(f"An error occurred. We are in analyze exception: {str(e)}")

    def html_to_xml(self, html_content: str) -> str:
        def clean_html_content(input_str):
            # Remove full HTML tags using regular expressions
            your_string = input_str.replace("<p>", "")
            your_string = your_string.replace("</p>", "")
            your_string = your_string.replace("<br>", "")
            your_string = your_string.replace("&nbsp;", "")
            your_string = your_string.replace("&amp;", "")
            your_string = your_string.replace("&lt;&gt;", "")

            return your_string

        xml_template = """<?xml version="1.0" ?>
                <request op="CLASSIFY">
                <document>
                    <body>&lt;?xml version=&quot;1.0&quot; encoding=&quot;UTF-8&quot;?&gt;
                &lt;story&gt;
                    &lt;headline&gt;{}&lt;/headline&gt;
                    &lt;headline_extended&gt;{}&lt;/headline_extended&gt;
                    &lt;body_html&gt;{}&lt;/body_html&gt;
                    &lt;slugline&gt;{}&lt;/slugline&gt;
                &lt;/story&gt;
                </body>
                </document>
                </request>
                """

        body_html = html_content["body_html"]
        headline = html_content["headline"]
        headline_extended = html_content["abstract"]
        slugline = html_content["slugline"]

        # Embed the 'body_html' into the XML template
        xml_output = xml_template.format(
            headline, headline_extended, body_html, slugline
        )
        xml_output = clean_html_content(xml_output)

        return xml_output


def init_app(app):
    Semaphore(app)
