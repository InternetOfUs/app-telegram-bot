# Contribute

## Language support

### Adding support for a new language

In order to add the support for a new language, the following steps should be completed.

1. Browse in the [translations](translations) folder.
2. Duplicate the `en` folder and name it with the code of the new language that should be added.
3. Edit the `messages.po` file by replacing the english texts with the new languages translations. 
    * Only texts associated to the `msgstr` should be changed,
    * Labels associated to `msgid` should not be changed.
    * [Poedit](https://poedit.net/) can help in handling the translations.
4. Once the changes are completed, compile the `messages.po` file. This will generate a `messages.mo` file.
    * [Poedit](https://poedit.net/) can help in building the `.mo` file.
5. Update the in the `ask_for_help_bot.main.py` adding the new line to the translator.

```python
from chatbot_core.translator.translator import Translator

translator = Translator("wenet-ask-for-help", alert_module, translation_folder_path, fallback=False)
translator.with_language("fa", is_default=False)
```

Please note how it is also possible to add aliases of a specific language. 
Here's what happens, for example, with the italian language:

```python
translator.with_language("it", is_default=False, aliases=["it_IT", "it_CH"])
```

6. Create a new pull request with your proposed changes. Please, make sure to deail your changes in the description.

### Edit translations for an already supported language

In order to propose changes to the translasion of an existing language, the following steps should be completed.

1. Browse in the [translations](translations) folder and into the folder of the language you would like to propose changes for.
2. Open the `messages.po` (we suggest using [Poedit](https://poedit.net/) or a similar application).
3. Identify the text you would like to change the translation for and apply your changes.
4. Compile the changes into an updated `messages.mo` file.
5. Create a new pull request with your proposed changes. Please, make sure to detail your changes in the description.

