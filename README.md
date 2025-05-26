# **Jarnhopur-GIM-Filter**
Jarnhopurs OSRS Loot Filter, targeted for GIM players, with minor UI/graphical changes.

I prefer the simplistic style of the default loot in OSRS but wanted to explore Loot Filters extreme customization, this led me to adding what I consider to be minor changes to the default expierience in terms of appearance while utilizing the power of the plugin for choosing what items appear when fighting certain monsters or in specific locations.

## [**Jarnhopur's GIM Team Filter**](https://github.com/Wizard12892/Jarnhopur-GIM-Filter/blob/main/filter.rs2f)
⚠️Still a work in progress⚠️
The "Published" version of the filter, the most refined version with (hopefully) the least amount of bugs.

## [**Jarnhopur's Python Parser**](https://github.com/Wizard12892/Jarnhopur-GIM-Filter/blob/main/Parser/Parsers.md)
I've created two seperate Python Scripts that parse data from the OSRS wiki using the API and compiles that data using templates to create data that Loot Filters can utilize.
The scripts pull drops from the monsters Loot Tables, sorts them into predefined categories and then formats that data so the filterscape website and the Loot Filters plugin can make use of.
        
The scripts also pull location data from the spawn locations of the monsters and uses that to define areas where Loot Filters can modify how the drops are displayed.

## [**Jarnhopur's Totally Working and Not Broken at all Filter**](https://github.com/Wizard12892/Jarnhopur-GIM-Filter/blob/main/testfilter.rs2f)
🚫The in progress, testing version of the filter. Always a work in progress, and probably broken half the time.🚫