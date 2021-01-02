# WIP PLACEHOLDER
rest soon(tm) code in another day or so...

# Secure Groups

Plugin for Auto Group Bot Stuffs for [Alliance Auth](https://gitlab.com/allianceauth/allianceauth).

## Features
 - Manual Groups, either auto add or still request add via Auths Built in Group Management system.
 - Auto Groups, process all members for a filter and add who ever passes.
 - A Grace on failure when already in the group system
 - Pings to users on discord and in auth when they are removed
 - Smart Group Filters included with this app:
   - Alt in Alliance on account
   - Alt in Corp on account

## Apps that provide a filter
Not in any particular order:
 - Corptools ( link here )
   - Assets on account
   - skills on account
   - some others i forget ATM
 - zkill module ( link )
   - Kills in time period
 - Blacklist module ( link )
   - users has no flags or has or has never had blacklisted chars

## Third Party Filters!
**This is the most minimal requirements and may in places be a bit pseudo currently**

The core premise of this module is to allow any 3rd party app add a filter to the options. This is achieved using a model from your app.

The "Key Model Assumptions" are as follows;
 - Your model **Must Have**:
   - `name` field
   - `description` field
   - `process_filter` function
 - `process_filter` will check the account of the `user` passed in relative to your apps data.
 - `process_filter` will always return a boolean, and NEVER throw exception.
 - `user` will be an auth user model ( add a link )

The process is essentialy as follows;
### Create a filter model "Filter Model"
My base filter is as follows.
**This is the most minimal requirements and may in places be a bit pseudo currently**

```python
class BaseFilter(models.Model):
    name = models.CharField(max_length=500) # This is the filters name shown to the admin
    description = models.CharField(max_length=500) # this is what is shown to the user

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.name}: {self.description}"

    def process_filter(self, user: User): # this is the check run against a users characters
        return NotImplemented("Please Create a filter!")
```

Now you create your filter! EG. A filter for checking if a users has a alt in a specific corp could look a little like this;

```python
class ExampleAltCorpFilter(FilterBase):
    alt_corp = models.ForeignKey(EveCorporationInfo, on_delete=models.CASCADE)

    def process_filter(self, user: User):
        try:
            character_list = user.character_ownerships.all().select_related('character')
            character_count = character_list.filter(character__corporation_id=self.alt_corp.altcorp_id).count()
            if character_count > 0:
                return True
            else:
                return False
        except:
            return False
```

### Add your new filter model to the admin site
it would look a little like this in our continuing example
```python
class ExampleAltCorpAdmin(admin.ModelAdmin):
    raw_id_fields = ['alt_corp']

admin.site.register(ExampleAltCorpFilter, ExampleAltCorpAdmin)
```

### Add hooks for your filter models
The magic happens by using a GenericForeignKey in this app to access your models in your app. You have to *tell us* about your apps filters for them to work, [here is how i manage the ones in this app.](Link to the repo signals file)

Continuing with the above example. for the hooks in your auth_hooks.py

```python
from .models import ExampleAltCorpFilter, ExampleOtherFilter, SomeOtherFilter

@hooks.register('secure_group_filters') # this is the critical name we are searching for.
def filters(): # can be any name
    return [ExampleAltCorpFilter, ExampleOtherFilter, SomeOtherFilter] # pass in the model classes as an array.

```

This will keep us all in sync and we can start using the filter! in a smart group, if you app goes away or a filter becomes obsolete it will simply be ignored till it returns or is deleted in admin.

## Screenshots

TODO: MAKE NEW SCREENSHOTS!

![https://cdn.discordapp.com/attachments/752362812176728147/794876785480171550/unknown.png](https://cdn.discordapp.com/attachments/752362812176728147/794876785480171550/unknown.png)

users display demo

![https://cdn.discordapp.com/attachments/656624103523876895/794835225904939008/unknown.png](https://cdn.discordapp.com/attachments/656624103523876895/794835225904939008/unknown.png)

discord message example

![https://cdn.discordapp.com/attachments/752362812176728147/794880515798466590/unknown.png](https://cdn.discordapp.com/attachments/752362812176728147/794880515798466590/unknown.png)

admin demo

![https://cdn.discordapp.com/attachments/656624103523876895/794835209249882122/unknown.png](https://cdn.discordapp.com/attachments/656624103523876895/794835209249882122/unknown.png)


## Issues
Please remember to report any Group Bot related issues using the issues on **this** repository.

## Contributing
Make sure you have signed the [License Agreement](https://developers.eveonline.com/resource/license-agreement) by logging in at https://developers.eveonline.com before submitting any pull requests. **All bug fixes or features must not include extra superfluous formatting changes.**
