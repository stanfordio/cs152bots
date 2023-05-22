from report import Report, BotReactMessage, State
from datetime import datetime
from enum import Enum, auto
import discord
import re

user_false_reports = {}
manual_check_queue = []


def new_report(completed_report, user_being_reported,
               user_making_report, reports_by_user, reports_about_user):
    some_condition = False  # temp placeholder for classifier
    # Check if abuse or not.
    is_abuse = False
    if some_condition:
        is_abuse = True

    if not is_abuse:
        # Add to false reporting map.
        if user_making_report not in user_false_reports:
            user_false_reports[user_making_report] = []
        user_false_reports[user_making_report].append(completed_report)

        # Check if user has > 30 false reports.
        if len(user_false_reports[user_making_report]) > 30:
            return False, ": Your account has been banned due to too many false reports."
        else:
            return False, ": We did not find this message to be abusive. " \
                          "Please contact us if you think we made a mistake."

    # Determine what type of abuse.
    reported_issues = completed_report.get_reported_issues()
    if reported_issues[0] == Report.HARASSMENT:
        return harassment_report(user_being_reported, user_making_report, reports_by_user, reports_about_user)
    elif reported_issues[0] == Report.SPAM:
        return spam_report(reports_about_user[user_being_reported])
    elif reported_issues[0] == Report.THREAT:
        threat_report(completed_report)
        return
    elif reported_issues[0] == Report.FRAUD:
        return fraud_report(completed_report, user_being_reported, user_making_report, reports_by_user,
                            reports_about_user)
    else:  # Other
        take_post_down, response = other_report(completed_report)
        return True, response


def harassment_report(user_being_reported, user_making_report, reports_by_user, reports_about_user):
    return True, strikes_against_user(reports_about_user[user_being_reported])


def spam_report(list_of_reports_against_user):
    # Check counts of spam already against user.
    spam_count = 0
    for report in list_of_reports_against_user:
        if report.reported_issues[0] is Report.SPAM:
            spam_count += 1

    if spam_count > 10:
        return True, "Your account has been banned due to too many spam messages."
    else:
        return True, "Your message was marked as spam and has been removed. "


def threat_report(completed_report):
    manual_check_queue.append(completed_report)


def fraud_report(completed_report, user_being_reported, user_making_report, reports_by_user, reports_about_user):
    reported_issues = completed_report.get_reported_issues()
    if reported_issues[1] == Report.IMPERSONATION:
        report_count = 0
        for report in reports_about_user[user_being_reported]:
            if (report.reported_issues[0] == Report.FRAUD) and ( report.reported_issues[1] == Report.IMPERSONATION):
                report_count += 1
        if report_count > 3:
            return True, "Your account has been banned due to reports of impersonation."
        else:
            manual_check_queue.append(completed_report)

    elif reported_issues[1] == Report.FALSE_INFO:
        manual_check_queue.append(completed_report)

    elif reported_issues[1] == Report.REQUESTED_MONEY:
        if reported_issues[2] == Report.OBTAINED_MONEY:
            manual_check_queue.append(completed_report)
            return False, "Your account is under review for "
        else:
            report_count = 0
            for report in reports_about_user[user_being_reported]:
                if (report.reported_issues[0] == Report.FRAUD) and (report.reported_issues[1] == Report.REQUESTED_MONEY):
                    report_count += 1
            if report_count > 3:
                return True, "Your account has been banned due to reports of monetary fraud."
            else:
                manual_check_queue.append(completed_report)
    else:
        return other_report(completed_report)


def other_report(completed_report):
    manual_check_queue.append(completed_report)
    response = "Your report has been placed in our queue for manual moderation"
    return response


def strikes_against_user(list_of_reports_against_user):
    non_spam_count = 0
    for report in list_of_reports_against_user:
        if report.reported_issues[0] != Report.SPAM:
            non_spam_count += 1

    if non_spam_count > 3:
        return "Your account has been banned due to too many harmful messages."
    else:
        return "Your message was marked as harmful and has been removed."

#to add functionality for checking if reporter history (if too many reports, ignore/offer to block)