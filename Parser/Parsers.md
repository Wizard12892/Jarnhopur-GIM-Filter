# Parsers and Supporting Files

##  **Parsers**
###     **Monster Parser**
    - The [Monster parser](https://github.com/Wizard12892/Jarnhopur-GIM-Filter/blob/main/Parser/parse_monsters.py) is for use with most monsters. It requires a [monsters list](https://github.com/Wizard12892/Jarnhopur-GIM-Filter/blob/main/Parser/monsters.txt) and a [monsters template](https://github.com/Wizard12892/Jarnhopur-GIM-Filter/blob/main/Parser/monster_template.txt) to function.
    - Firstly I setup a list of monsters, this list is fully customizable and the script should handle any monster on the wiki. I have mine setup in two sections, Non-Slayer monsters assigned by slayer masters, and Slayer monsters. To me this covers most monsters that I would conceivably kill in my day to day play.
        * Some monsters I categorized into Groups for ease of use, IE Trolls and Spiritual Creatures. The script will pull the drops for all of the included variants and combine the lists under the group module in the filter.
            
    - The Monster script will pull loot from the wiki and seperate it into several categories.
        * Always - 100% Drops.
        * Weapons and Armour
        * Runes and Ammunition
        * Materials - Materials encompasses a broad range of categories, essentially anything that can be used.
        * Other - Miscellanous drops as labeled on the wiki.
        * Tertiary
            Notes: The script ignores Coins as I deal with those seperately in my filter.
            : It also does not pull any drops from the Rare drop table as I thought that would add too many items to most monsters, they are also caught by my personal filter.
    - The filter also defines locations where the monsters can be found
        * It uses spawn coordinates from the wiki, it groups the spawns by location, searches for adjacent groups within 32 blocks and combines the groups if found.
        * Then it adds a 10 block buffer zone in all directions to try and account for wander range. [I don't expect this to perfectly enclose every location but I hope it gets decently close.] 
    - Lastly it formats all of that data using a template to organize and display the data in a way that [Filterscape](https://filterscape.xyz/) and [Loot Filters](https://runelite.net/plugin-hub/show/loot-filters) can utilize. 

###     **Boss Parser**
    - The [Boss parser](https://github.com/Wizard12892/Jarnhopur-GIM-Filter/blob/main/Parser/parse_bosses.py) is for use with Bosses. It requires a [list of bosses](https://github.com/Wizard12892/Jarnhopur-GIM-Filter/blob/main/Parser/bosses.txt) and a [boss template](https://github.com/Wizard12892/Jarnhopur-GIM-Filter/blob/main/Parser/boss_template.txt) to function.
    - The functionality is basically identical to that of the monster parser. However it required some different code to handle the more unique edge cases that Bosses have over standard mobs.
    - My boss list is seperated into 4 categories to aide in finding the specific boss you're looking for. Standard Bosses, Wildy Bosses, DT2 Bosses, and Slayer Bosses. (As I'm writing this I don't know why I didn't seperate GWD Bosses as well 🤷‍♂️)
    - The Drops have 2 additional categories
        * **Uniques** - This combines Unique drops and Pre=Roll drops into a single category.
        * Always - 100% Drops.
        * **Supplies** - Items you might want to pick up to extend your trips.
        * Weapons and Armour
        * Runes and Ammunition
        * Materials - Materials encompasses a broad range of categories, essentially anything that can be used.
        * Other - Miscellanous drops as labeled on the wiki.
        * Tertiary
    - Several Bosses don't have spawn information listed on the wiki and their locations are hard coded into the script. Currently these are Grotesque Guardians, Nex, Yama, and Zulrah.
    - Most other differences are completely script side and typically don't effect the output in any noticeable manner.

###     **Customization**
    - The formatting for Monster Groups is <Group Name> {Variant1; Variant2; Variant3} These can be added or removed in the monster lists txt file at your leisure.
    - The Drop categories are listed in a library at the begining of the script and can be edited to fit your specific desires. My materials category for example could be broken down in Herbs, Seeds, Ores, Bars, etc allowing more detailed customization.
        ! However there are a lot of edge cases in wiki loot that need to be individually assigned to categories. IE Vorkath has a drop table titled 'Dragonhide' that won't be sorted unless specified in the library.
    - The adjacent group range (Default: 32 Blocks) and the wander range (Default: 10 Blocks) are both defined constants and can easily be edited in the python script.
    - The template is also completely customizable. You can change the categories it displays, the order they appear in, and add in any other Loot Filters module customization you would like.
    - Each module is encased by // START and // END tags, these allow the script to remove modules for monsters that don't have any drops in that category.

###     **Miscellaneous**
    - Much of the code in the scripts is to clean up the data parsed from the wiki and extract the information in a useable manner. Comments are included in much of the code blocks if you'd like to review it for yourself.
    - While I have a mild understanding of code much of these scripts were created with the help of AI. If you notice something that doesn't perform as intended or can be optimized in some way please let me know.