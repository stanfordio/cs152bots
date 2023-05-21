class GenericMessage:
    INVALID_YES_NO = "I'm sorry, I didn't understand that. Please type `yes` or `no`."
    INVALID_RESPONSE = (
        "I'm sorry, I didn't understand that. Please try again or type `cancel` to"
        " cancel."
    )
    INVALID_REACTION = (
        "I'm sorry, I didn't understand that reaction. Please try again or type `cancel`"
        " to cancel the report."
    )
    CANCELED = "Report canceled."
    REPORT_COMPLETE = (
        "Thank you for reporting this activity. Our moderation team will review your"
        " report and contact you if needed. No further action is required on your part."
    )
    INVALID_SKIP = (
        "I'm sorry. This question cannot be skipped. Please choose an option or type"
         " `cancel` to cancel the report."
    )


class ReportStartMessage:
    START = (
        "Thank you for starting the reporting process. Type `help` at any time for more"
        " information or `cancel` to cancel the report."
    )
    REQUEST_MSG = (
        "Please copy paste the link to the message you want to report.\nYou can obtain"
        " this link by right-clicking the message and clicking `Copy Message Link`."
    )
    INVALID_LINK = (
        "I'm sorry, I couldn't read that link. Please try again or type `cancel` to"
        " cancel."
    )
    NOT_IN_GUILD = (
        "I cannot accept reports of messages from guilds that I'm not in. Please have"
        " the guild owner add me to the guild and try again."
    )
    CHANNEL_DELETED = (
        "It seems this channel was deleted or never existed. Please try again or type"
        " `cancel` to cancel the report."
    )
    MESSAGE_DELETED = (
        "It seems this message was deleted or never existed. Please try again or type"
        " `cancel` to cancel the report."
    )
    MESSAGE_IDENTIFIED = (
        "I found this message:\n```{author}: {content}```\nIs"
        " this the message you want to report? Please type `yes` or `no`."
    )


class UserDetailsMessage:
    ON_BEHALF_OF = (
        "Are you reporting on behalf of someone else? Please type `yes` or `no`."
    )
    WHO_ON_BEHALF_OF = "Who are you reporting on behalf of?"


class ReportDetailsMessage:
    REASON_FOR_REPORT = (
        "Please select the reason for reporting this message. React to this message"
        " with the corresponding emoji.\n1️⃣ - Harassment or offensive content \n2️⃣ - Spam"
        " \n3️⃣ - Immediate danger\n4️⃣ - Other"
    )
    ABUSE_TYPE = (
        "What type of abuse are you reporting? React to this message with"
        " the corresponding emoji.\n1️⃣ - Sexually explicit harassment\n2️⃣ - Encouraging"
        " self-harm\n3️⃣ - Hate speech\n4️⃣ - Other"
    )
    ABUSE_DESCRIPTION = (
        "Which of the following best describes the situation? React to this"
        " message with the corresponding emoji.\n1️⃣ - The reporting user is receiving"
        " sexually explicit content (images, text)\n2️⃣ - The reporting user is receiving"
        " unwanted requests involving sexually explicit content"
    )
    UNWANTED_REQUESTS = (
        "What is the account you are reporting requesting? React to this"
        " message with the corresponding emoji.\n1️⃣ - Money\n"
        "2️⃣ - Additional sexually explicit content\n3️⃣ - Other"
    )
    MULTIPLE_REQUESTS = (
        "Have you or the person on behalf of whom this report is being filed received multiple"
        " requests from the account you are reporting? Please type `yes` or `no`."
    )
    APPROXIMATE_REQUESTS = (
        "Please approximate the number of requests."
    )
    COMPLIED_WITH_REQUESTS = (
        "Have you or the person on behalf of whom this report is being filed complied"
        " with these requests? Please type `yes` or `no`."
    )
    MINOR_PARTICIPATION = (
        "Does the sexually explicit content involve a minor? Please type `yes` or `no`."
    )
    CONTAIN_YOURSELF = (
        "Does this content contain you or the person on behalf of whom this report is being"
        " filed? Please type `yes` or `no`."
    )
    ENCOURAGE_SELF_HARM = (
        "Is the account you are reporting encouraging self-harm? Please type `yes`, `no`, or"
        " `skip` to skip this question."
    )
    SELF_HELP_RESOURCES = (
        "self-help: idk"
    )
    ADDITIONAL_INFO = (
        "Would you like to provide any additional information? Please type `yes` or `no`."
    )
    PLEASE_SPECIFY = (
        "Please specify."
    )
    BLOCK_USER = (
        "Would you like to block the account you have reported? Please type `yes` or `no`."
    )
    BLOCKED = (
        "`{author}` has been blocked."
    )
    CONFIRMATION = (
        "show current report. \n"
        "Please type `yes` or `no` to confirm that you would like to submit this report."
    )