# CHANGELOG December, 2014

### ADDITIONS

* Login functionality to database (email only used for uniqueness)
  * Uses google (need gmail account) to handle authentication
  * Set username by clicking the dude next to the login button
  * Logging in gives uploaded maps "ownership"
  * When submitting maps and logged in, the map's author will change to your username

* Ability to delete maps that you uploaded when logged in
* Ability to pick texture pack that your maps are rendered in
* Ability to pick default test server (when set, clicking 'test' will use your default)
* Added all texture packs that worked easily from wiki
* 45 degree tile preview (thanks GreenVars!)
* Commenting system for maps (need to be logged in to add comment)
* Ability to allow / disallow feedback on map
* Map Voting
* Versioning - when you submit a map with the same map name, it will be added as a version to your map
  * This lets you upload 10 maps with the same name, making minors changes, and not clog up the recent page
  * If you go to your profile, you will see all the maps that you've submitted
* Primary mode: Pick which version you want to have displayed
* Added link to /r/tagpromapsharing
* Integrated Map Editor into juke juice - save directly to juke juice, remix maps from juke juice in the editor
* Your selected texture will be available in the map editor



#### BUG FIXES
* When searching, pagination now works properly (bringing you to page 2 with query, rather than new maps)
* Altered the 'showmap' page - before the image link would take up too much space
..* The image link doesn't show, but clicking a map image will bring you to the full size preview
