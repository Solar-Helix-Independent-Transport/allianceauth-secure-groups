## Third Party Filters!
**This is the most minimal requirements and may in places be a bit pseudo currently**

The core premise of this module is to allow any 3rd party app add a filter to the options. This is achieved using a model from your app.

Please keep a few key design factors in mind. Consider these Loose Rules:
 - A filter should never hit the network.
   - As we could be running thousands of these in very quick succession we domt want to have issues with network/blacklists
 - A filter should be gentle to the database.
   - where possible keep the amount of db queries to a minimum.

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
My base filter is as follows. [View the Real Code Here](https://github.com/pvyParts/allianceauth-secure-groups/blob/main/securegroups/models.py#L49)

**This is the most minimal requirements and may in places be a bit pseudo currently**
I do not recommend you import this model as it will create a dependency on your app. You have been warned.

```python
class BaseFilter(models.Model):
    name = models.CharField(max_length=500) # This is the filters name shown to the admin
    description = models.CharField(max_length=500) # this is what is shown to the user

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.name}: {self.description}"

    def process_filter(self, user: User): # this is the check run against a users characters
        raise NotImplementedError("Please Create a filter!")
```

Now you create your filter! EG. A filter for checking if a users has a alt in a specific corp could look a little like this; [View the Real Code Here](https://github.com/pvyParts/allianceauth-secure-groups/blob/main/securegroups/models.py#L64)

```python
class ExampleAltCorpFilter(BaseFilter):
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

Continuing with the above example. for the hooks in your auth_hooks.py. [View the Real Code Here](https://github.com/pvyParts/allianceauth-secure-groups/blob/main/securegroups/auth_hooks.py#L35)

```python
from .models import ExampleAltCorpFilter, ExampleOtherFilter, SomeOtherFilter

@hooks.register('secure_group_filters') # this is the critical name we are searching for.
def filters(): # can be any name
    return [ExampleAltCorpFilter, ExampleOtherFilter, SomeOtherFilter] # pass in the model classes as an array.

```

This will keep us all in sync and we can start using the filter! in a smart group, if you app goes away or a filter becomes obsolete it will simply be ignored till it returns or is deleted in admin.
