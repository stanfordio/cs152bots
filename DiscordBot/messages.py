class GenericMessage:
    INVALID_YES_NO = "I'm sorry, I didn't understand that. Please say `yes` or `no`."
    INVALID_RESPONSE = (
        "I'm sorry, I didn't understand that. Please try again or say `cancel` to"
        " cancel."
    )
    INVALID_REACTION = (
        "I'm sorry, I didn't that reaction. Please try again or say `cancel` to cancel."
    )
    CANCELED = "Report canceled."


class ReportStartMessage:
    START = (
        "Thank you for starting the reporting process. Say `help` at any time for more"
        " information."
    )
    REQUEST_MSG = (
        "Please copy paste the link to the message you want to report.\nYou can obtain"
        " this link by right-clicking the message and clicking `Copy Message Link`."
    )
    INVALID_LINK = (
        "I'm sorry, I couldn't read that link. Please try again or say `cancel` to"
        " cancel."
    )
    NOT_IN_GUILD = (
        "I cannot accept reports of messages from guilds that I'm not in. Please have"
        " the guild owner add me to the guild and try again."
    )
    CHANNEL_DELETED = (
        "It seems this channel was deleted or never existed. Please try again or say"
        " `cancel` to cancel."
    )
    MESSAGE_DELETED = (
        "It seems this message was deleted or never existed. Please try again or say"
        " `cancel` to cancel."
    )
    MESSAGE_IDENTIFIED = (
        "I found this message:\n```{author}: {content}```\nIs"
        " this the message you want to report? Please say `yes` or `no`."
    )


class UserDetailsMessage:
    ON_BEHALF_OF = (
        "Are you reporting on behalf of someone else? Please say `yes` or `no`."
    )
    WHO_ON_BEHALF_OF = "Who are you reporting on behalf of?"


class ReportDetailsMessage:
    REASON_FOR_REPORT = (
        "Please select the reason for reporting this message. React to this message"
        " with the corresponding emoji.\n1️⃣ - Harassment or offensive content \n2️⃣ - Spam"
        " \n3️⃣ - Immediate danger\n4️⃣ - Other"
    )
    ABUSE_TYPE = (
        "Please select the type of abuse you are reporting. React to this message with"
        " the corresponding emoji.\n1️⃣ - Sexually explicit harassment\n2️⃣ - Encouraging"
        " self-harm\n3️⃣ - Hate speech\n4️⃣ - Other"
    )
