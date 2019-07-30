# Complete workflow of new PyLadies chapter

## Step 0: A request come in through Google Spreadsheet :raising_hand_woman:

1. Prospective organizer read through the [PyLadies kit for prospective organizers](http://kit.pyladies.com/en/latest/prospective/index.html)

2. Prospective organizer submitted their request for new chapter [by filling in the form](https://docs.google.com/forms/d/e/1FAIpQLSeOL0xgRD6jwV3RJxFNApdT_qQN1-3uNomRK4XTfUKSaeDhNg/viewform).

3. :robot: PyLadies-bot posts the request to #feed-new-chapter in Slack. To help speed up the process, the bot also did a quick scan of the spreadsheet, to see if chapter with same namespace already exists.

4. :robot: PyLadies Info automatically reply back with message: "thanks for filling in the form, we will review it and get back to you etc)"

## Step 1: Check if chapter exists :warning:

### 1.1: If no chapter yet

1. Ensure the namespace is descriptive/city-based. E.g. "sao paulo" instead of "sp". "beijing" instead of "china". 
2. Review at next PyLadies Global Meeting once a month.

### 1.2: If the chapter already exists:

1. It may not be active, hence the request. Write email to existing organizers to ask about status. Ask if they want to continue/open in having a co-organizer.
2. If no reply after 7 days, consider it inactive, and review the request at next PyLadies Global Meeting once a month.

## Step 2: PyLadies leadership will review requests on monthly basis at global meeting

1.:question: **TBD**: How do we decide whether to approve/reject? What are our guidelines/criteria for new chapter?

## Step 3: Create the namespace in admin.google.com

1. Create the @pyladies.com email address, if it doesn't exist.
2. Create new password, (or reset the password, in case of inactive chapter) and tick the "reset password at next login".
3. Add these info as a new row to the **new chapter (for bot)** tab in the "Initial PyLadies interest" spreadsheet.
   
   :rotating_light: **IMPORTANT**: The magic column in this tab is the **"ready to send?"** column. :rotating_light:
   
   If you enter, **yes** in that column, bot will start working and do the following:

   1. :robot: Write welcome email to the new organizer (congrats etc)
   2. :robot: Write a separate email containing credentials to @pyladies.com email address
   3. :robot: Announce the new chapter to slack #general channel
   4. :robot: Post to slack #organizers channel about the new chapter
   5. :tada:
   
