# Contribute to the _Ask For Help_ chatbot

## Contribute by adding support for a new language

In order to add the support for a new language you should:

1. look at the [translations](translations) folder in which there are sub-folders named with the code of the languages supported.
2. make a copy of the `en` folder and renaming it with the code of the language you want to add.
3. edit the `messages.po` file by adding your translations, for example by using a program like [Poedit](https://poedit.net/).
4. compile the `messages.po` file in order to generate the `messages.mo` file that will be used in the translations. This can be done for example by using a program like [Poedit](https://poedit.net/).
5. add in the `ask_for_help_bot.main` file a line under the exiting translations specifying your language code. For example, if the code of the language you are adding is `fa` you should add:
```
translator.with_language("fa", is_default=False)
```
You can also add aliases in case the code of the language depends also on the countries where the language is spoken. For example, you can take inspiration from:
```
translator.with_language("it", is_default=False, aliases=["it_IT", "it_CH"])
```
6. test that the translations work as expected on your local machine.
7. update the [CHANGELOG](CHANGELOG.md) by specifying what changes you have done.
8. create a pull request with your proposed changes.
