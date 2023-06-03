from report import Report, BotReactMessage, State
from datetime import datetime
from enum import Enum, auto
import discord
from bot import money_message, impersonating

user_false_reports = {}
manual_check_queue = []

HIGHEST_PRI = 1
HIGH_PRI = 2
MED_PRI = 3
LOW_PRI = 4

# possible actions: NO_ACTION, MANUAL, BAN, SUSPEND


def new_report(completed_report, user_being_reported, user_making_report, reports_about_user):
    is_abuse = False
    if some_condition:  # to do - send this condition from bot.py
        is_abuse = True

    if not is_abuse:
        # Add user to false reporting map
        if user_making_report not in user_false_reports:
            user_false_reports[user_making_report] = []
        user_false_reports[user_making_report].append(completed_report)

        # If user has a history of false reports ban them
        if len(user_false_reports[user_making_report]) > 10:
            return 'BAN', ": Your account has been banned due to too many false reports.", LOW_PRI
        else:
            return 'NO_ACTION', ": We did not find this message to be abusive. " \
                          "Please contact us if you think we made a mistake.", LOW_PRI

    # Check abuse type
    reported_issues = completed_report.get_reported_issues()
    if reported_issues[0] == Report.HARASSMENT:
        return harassment_report(user_being_reported, user_making_report)
    elif reported_issues[0] == Report.SPAM:
        return spam_report(reports_about_user[user_being_reported])
    elif reported_issues[0] == Report.THREAT:
        return threat_report(completed_report)
    elif reported_issues[0] == Report.FRAUD:
        return fraud_report(completed_report)
    else:  # Other
        action, response, severity = other_report(completed_report)
        return action, response, severity


def harassment_report(user_being_reported, reports_about_user):
    return strikes_against_reported_user(reports_about_user[user_being_reported])


def spam_report(list_of_reports_against_user):
    spam_count = 0
    for report in list_of_reports_against_user:
        if report.reported_issues[0] is Report.SPAM:
            spam_count += 1

    if spam_count > 10:  # user has been reported many times for spam
        return 'BAN', "Your account has been banned due to too many spam messages.", MED_PRI
    else:
        return 'SUSPEND', "Your account has been suspended due to reports of spam messages. ", MED_PRI


def threat_report(completed_report):
    manual_check_queue.append(completed_report)
    return 'MANUAL', "", HIGHEST_PRI


def fraud_report(completed_report):
    reported_issues = completed_report.get_reported_issues()

    if reported_issues[1] == Report.IMPERSONATION:
        if impersonating(completed_report.get_reported_message()) == "yes":
            return 'BAN', "Your account has been banned due to reports of impersonation.", HIGH_PRI
        else:
            manual_check_queue.append(completed_report)
            return 'MANUAL', "Your account is under review due to reports of fraud.", MED_PRI

    elif reported_issues[1] == Report.FALSE_INFO:
        manual_check_queue.append(completed_report)
        return 'MANUAL', "Your account is under review due to reports of fraud.", LOW_PRI

    elif reported_issues[1] == Report.REQUESTED_MONEY:
        if reported_issues[2] == Report.OBTAINED_MONEY:  # requested and obtained money
            manual_check_queue.append(completed_report)
            return 'MANUAL', "Your account is under review due to reports of fraud.", HIGH_PRI
        else:  # requested but did not obtain money
            if money_message(completed_report.get_reported_message()) == "yes":
                return 'BAN', "Your account has been banned due to reports of monetary fraud.", HIGH_PRI
            else:
                manual_check_queue.append(completed_report)
                return 'MANUAL', "Your account is under review due to reports of fraud", MED_PRI
    else:
        return other_report(completed_report)


def other_report(completed_report):
    manual_check_queue.append(completed_report)
    response = "Your report has been placed in our queue for manual moderation."
    return 'MANUAL', response, LOW_PRI


def strikes_against_reported_user(list_of_reports_against_user):
    non_spam_count = 0
    for report in list_of_reports_against_user:
        if len(report.reported_issues) > 1 or report.reported_issues[0] != Report.SPAM:
            non_spam_count += 1

    if non_spam_count > 3:  # many reports of fraud
        return 'BAN', "Your account has been banned due to too many harmful messages.", HIGH_PRI
    else:  # first time offender
        return 'SUSPEND', "Your message was marked as harmful, you have been suspended " \
                          "for 15 days. Please contact us if you think we made a mistake.", MED_PRI