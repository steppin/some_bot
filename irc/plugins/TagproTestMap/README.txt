Start test games for custom maps in TagPro from irc!

Testing
=======

Setup
-----

1. Create the somebot_test db.
    ```
    sudo -u postgres createdb somebot_test --owner steppin
    ```

2. Rus supybot-test.
    ```
    cd irc/plugins
    supybot-test TagproTestMap
    ```

    Unfortunately, supybot has a bug where config settings in test.py are not applied until after __init__ is called.  This will cause your tests to fail.  Ask me for a patch.  I am working on getting this integrated upstream but it's tough as supybot devel has stagnated.
