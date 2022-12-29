# Discord Meme Bot
Comprehensive discord meme storage bot using DynamoDB, run on EC2

Each meme requires a unique keyword to be stored, and can be recalled using the same keyword. Users are able to provide a keyword, description, and category to classify memes through the ```add``` command.

In addition to quick storage, this bot facilitates easy retrieval, even when a certain keyword cannot be remembered. Users can search for phrases present in keywords, descriptions, and even text present in the images through optical character recognition, using Pytesseract. The bot is also aware of what media is already present by hashing new memes to see if that image hash has already been added using the ImageHash library.

Some quality-of-live updates include the addition of blacklists (rolling random does not yield memes of blacklisted categories), the addition of profile picture emojis for users in the server, and a server leaderboard displaying users with the most additions.

# Quick walkthrough
https://user-images.githubusercontent.com/52140136/209906887-39c5bb96-2d28-4dcf-89bb-e9aa2f72f890.mov

# Commands
The bot supports the following commands:

```add```:       Stores last media recently sent by user using specified keyword.

```allcats```:   Sends embed containing list of all categories.

```blacklist```: Sends embed containing list of categories blacklisted by user.

```cat```:       Add item specified by keyword to a category.

```delcat```:    Deletes category if less than 10 items or if user is admin.

```delete```:    Deletes media associated with keyword from database.

```desc```:      Add or change description of keyword.

```emoji```:     Sets user's emoji to emoji or reports current emoji.

```get```:       Gets media from specified keyword.

```help```:      Shows a message listing all the commands

```hide```:      Makes media in category hidden for user when rolling random.

```keys```:      Displays all keywords in database or in specified category.

```last```:      Outputs information of last media sent.

```like```:      Add specified keyword to user's list of liked items.

```memes```:     Send embed containing list of memes added by specified user.

```myliked```:   Sends embed displaying list of user's liked memes.

```newcat```:    Add new category for items in database.

```put```:       Stores media in database using specified keyword.

```random```:    Sends media corresponding to a random keyword.

```rank```:      Send embed ranking members by number of items added.

```search```:    Sends embed containing all media with specified string.

```show```:      Makes media in category unhidden for user when rolling random.

```top```:       Displays list of top 20 liked keywords

```unlike```:    Remove specified keyword from user's list of liked items.
