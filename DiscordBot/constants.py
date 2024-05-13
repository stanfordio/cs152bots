from enum import Enum, auto

class UserResponse(Enum):
    ABUSE_TYPE = "abuse_type"
    SPEC_ISSUE = "specific_issue"
    SOURCE = "source"
    FINAL_NOTE = "final_note"

class SpecificIssue(int):
    DISINFORMATION = 1
    ADULT = 2
    ILLEGAL = 3
    OFFENSIVE = 4
    OTHER = 5
    POLITICAL = 5

USER_REPORT_KEY = {
    1: {
        "name": "Misleading or False Information",
        1: "Deepfakes and deceptive AI-generated content",
        2: "Deceptive offers",
        3: "Impersonation",
        4: "Manipulated Media",
        5: "Political Disinformation"
    },
    2: {
        "name": "Inappropriate Adult Content",
        1: "Nudity and sexual content",
        2: "Adult products and/or services",
        3: "Sensitive content"
    },
    3: {
        "name": "Illegal Products or Services",
        1: "Banned substances/drugs",
        2: "Unauthroized medical products",
        3: "Weapons or explosives",
        4: "Illegal activities/services"
    },
    4: {
        "name": "Offensive Content",
        1: "Profanity",
        2: "Hate speech",
        3: "Violent imagery"
    },
    5: {
        "name": "Other",
        1: "Technical issues",
        2: "Privacy issues",
        3: "Feedback on ad preferences",
        4: "Other concerns"
    }
}