# Secure Groups

Plugin for Auto Group Bot Stuffs for [Alliance Auth](https://gitlab.com/allianceauth/allianceauth).

On its own this app does very little! However it leverages any module that is capable of providing a filter. Giving you the ability to add a very wide range of automatic filtration options your groups.

## Features

- Manual Groups, either auto join or still request join via Alliance Auth's Built in Group Management system.
- Auto Groups, process all member states for a filter and add/remove who ever passes/doesn't.
- A Grace on failure feature when already in the group with notifications to users to alow time to rectify
- Pings to users on discord and in auth when they are due for and removed
- Smart Group Filters included with this app:
  - Character in Alliance on account
  - Character in Corp on account
  - User has group

## Apps that provide a filter

Information for Third Party Developers can be found [Here](https://github.com/pvyParts/allianceauth-secure-groups/blob/main/THRID_PARTY.md)
Not in any particular order:

- [CorpTools](https://github.com/pvyParts/allianceauth-corp-tools/)
  - Assets in Locations
  - Skill List checks
  - Main's Time in Corp
  - All characters loaded in corp-tools
- [Statistics](https://github.com/pvyParts/allianceauth-analitics)
  - zKill - x Kills in x Months
- Blacklist module ( link )
  - users has no flags or has or has never had blacklisted char
- [Member Audit](https://gitlab.com/ErikKalkoken/aa-memberaudit) via its [integration](https://gitlab.com/eclipse-expeditions/aa-memberaudit-securegroups).
  - Activity Filter
  - Asset Filter
  - Character Age Filter
  - Member Audit Compliance Filter
  - Skill Set Filter
  - Skill Point Filter

## Soon(tm) Wishlist

- Filter for PAP's per Time Period
- Please request any "filters" you feel are worthwhile.

## Installation

### Install

1. `pip install allianceauth-securegroups`
2. edit your `local.py` amd add `'securegroups',` to `INSTALLED_APPS`
3. run migrations `python myauth/manage.py migrate securegroups`
4. restart auth `supervisorctrl restart all`
5. create the update task by running `python myauth/manage.py setup_securegroup_task`
    - this will create a daily task to run all your smart group checks. you cam edit this schedule as you desire from withing the admin site. `Admin > Periodic Tasks > Secure Group Updater`

### Configuration

1. Create an Auth Group. `Admin > Group Management > Group > Add Group.`
    - WARNING: There is a bug in auth that will wipe andy "AuthGroup" Settings on first save, to get around this, Set your groups name then click save and continue, then edit the rest of the settings.
    - Group Settings:
      - The Smart Group will override the important ones.
        - Hidden On, Internal Off, Public Off
      - The rest of the settings are observed as per Alliance Auth's normal group behavior
        - Open: Setting this will let anyone that passes the checks to join without a manager approval.
      - States:
        - Set states here to limit auto groups to specific states
        - Having no states will make an autogroup run against the entire user base. ( this is not recommended )
2. Create your Smart Filters
    - These will be in admin but can be under many apps that may provide a 3rd party filter
    - Create the filter and add your options as needed.
3. Set any Filters "Grace Periods", `Admin > Secure Groups > Smart Filters`
    - the default is 5 Days.
    - 0 is no grace.
    - after the elapsed time the user will be removed.
4. Setup the Smart Group `Admin > Secure Groups > Smart Groups > Add Smart Group`
    - Group: pick group from step one
    - Description *Optional*: to add to the group description in list
    - Filters: pick your Smart Filters from Step 2
    - Enabled: Turning this off Smart Groups don't show im the groups screen or run in any tasks
    - Can Grace: Turning this off overrides all grace periods for Instant Kick during updates.
    - Auto Group: Hides the group from the Secure Groups list, and will run every user in "member" States and constantly keep it in sync.
    - Include In Updates: Setting this off will alow you to have a check om join and never again style group.

### Notifications

- You can send a simple update log to a discord webhook
  - set these up in `Admin > Secure Groups > Group Update Webhooks > Add Group Update Webhook`
  - If you are using the AllianceAuth Discord Bot from [Here](link) users will be notified of pending removals and or removals from groups via DM's from the bot with an explanation. This requires no configuration.

## Screenshots

### Admin Setup of Smart Groups

![img](https://i.imgur.com/WzaI7bN.png)

### User Group Selection

![img](https://i.imgur.com/i4lMpLe.png)

### User Failed Checks

![img](https://i.imgur.com/vpeF3JP.png)

### User Passed Checks

![img](https://i.imgur.com/BiB6SdN.png)

### Audit Secure Groups

![img](https://i.imgur.com/mS11rwA.png)
![img](https://i.imgur.com/mzg7UcM.png)
![img](https://i.imgur.com/fjYut7x.png)

### Discord Message Example

![img](https://i.imgur.com/fxnacZj.png)

## Issues

Please remember to report any Secure Groups related issues using the issues on **this** repository.

## Contributing

Make sure you have signed the [License Agreement](https://developers.eveonline.com/resource/license-agreement) by logging in at [EVE Developers](https://developers.eveonline.com) before submitting any pull requests. **All bug fixes or features must not include extra superfluous formatting changes.**
