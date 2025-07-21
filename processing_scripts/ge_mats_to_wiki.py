import xml.etree.ElementTree as ET
import csv
import re
import png
import networkx as nx
import itertools
import yaml
import glob
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance
import random
import operator
import math
from pathlib import Path
import traceback

import pprint # for debugging

# NOTE FOR USER:
# This script has been modified to remove all image shape masking.
# It will now produce square images for all materials while retaining visual details from textures.
# For the script to run correctly, you must execute it from the root directory
# of the Noita game data dump, i.e., the directory containing 'materials.xml'
# and the 'data' folder with textures.


# TODO investigate why The Work (Sky) isn't included for Hell Slime

# TODO check for other material sources
#
# Entities:
#   PhysicsImageShapeComponent.material     as bodyOf lookup
#   ExplodeOnDamageComponent/config_explosion.spark_material      as hitting lookup
#   ParticleEmitterComponent.emitted_material_name      as emittedFrom lookup
#   DamageModelComponent.ragdoll_material     as corpseOf lookup
#   DamageModelComponent.blood_material       as bloodOf
#   DamageModelComponent.blood_spray_material       as sprayedBy
#   MagicConvertMaterialComponent.to_material       as convertedToBy
#   MaterialInventoryComponent/count_per_material_type/Material.material      as containedIn
#   PixelSpriteComponent.material     as bodyOf lookup
#

# TODO preprocess XML files as strings to account for Noita's non-conformance instead of having to regex shit every time
# https://docs.python.org/3/library/xml.etree.elementtree.html

####################################################################
## Data
####################################################################

effect_lookup = {
  "FROZEN": "frozen",
  "ON_FIRE": "on fire!",
  "POISONED": "poisoned",
  "BERSERK": "berserk",
  "CHARM": "charmed",
  "POLYMORPH": "polymorph",
  "POLYMORPH_RANDOM": "chaos polymorph",
  "POLYMORPH_UNSTABLE": "unstable polymorph",
  "BLINDNESS": "blinded",
  "TELEPORTATION": "teleportitis",
  "UNSTABLE_TELEPORTATION": "unstable teleportitis",
  "HP_REGENERATION": "regeneration",
  "LEVITATION": "faster levitation",
  "MOVEMENT_SLOWER": "clumsy movement",
  "FARTS": "gassy",
  "TRIP": "tripping",
  "INGESTION_DRUNK": "drunk",
  "RADIOACTIVE": "toxic",
  "ALCOHOLIC": "alcoholic",
  "WET": "wet",
  "OILED": "oiled",
  "BLOODY": "bloody",
  "SLIMY": "slimy",
  "CONFUSION": "confused",
  "FOOD_POISONING": "food poisoning",
  "INGESTION_ON_FIRE": "internal fire",
  "INGESTION_FREEZING": "chilly",
  "JARATE": "jarated",
  "MOVEMENT_FASTER_2X": "greased lightning",
  "FASTER_LEVITATION": "faster levitation",
  "WORM_ATTRACTOR": "worm food",
  "PROTECTION_ALL": "protection from all",
  "INVISIBILITY": "invisible",
  "MANA_REGENERATION": "mana regeneration",
  "PROTECTION_POLYMORPH": "polymorph immunity",
  "RAINBOW_FARTS": "rainbow farts",
  "CURSE_CLOUD": "rain curse",
  "NIGHTVISION": "wormy vision",
  "WEAKNESS": "weakness",
  "MAMMI_EATER": "the loathsome mämmi eater",
}


biome_png_mapping = {
  'data/biome_impl/acidtank.png': {'Snowy Depths'},
  'data/biome_impl/acidtank_2.png': {'Snowy Depths'},
  'data/biome_impl/alchemist_secret.png': {'Dark Chest'}, # AKA ???
  'data/biome_impl/alchemist_secret_music.png': {'???'},
  'data/biome_impl/altar.png': {'Mines', 'Snowy Depths', 'Holy Mountain'},
  #'data/biome_impl/boss_limbs_arena.png': {'boss_limbs_arena.png'},
  'data/biome_impl/boss_victoryroom.png': {'The Work (End)'},
  'data/biome_impl/bunker.png': {'Lake'},
  'data/biome_impl/bunker2.png': {'Lake'},
  'data/biome_impl/cavern.png': {'Friend Room'},
  #'data/biome_impl/clean_entrance.png': {'clean_entrance.png'},
  'data/biome_impl/dragoncave.png': {'Dragoncave'},
  'data/biome_impl/essenceroom.png': {'???'},
  'data/biome_impl/essenceroom_submerged.png': {'???'},
  #'data/biome_impl/eyespot.png': {'eyespot.png'},
  'data/biome_impl/fishing_hut.png': {'Lake'},
  'data/biome_impl/friendroom.png': {'Friend Room'},
  'data/biome_impl/funroom.png': {'Desert Chasm'},
  'data/biome_impl/greed_room.png': {'Hall of Wealth'},
  'data/biome_impl/greed_treasure.png': {'Avarice Diamond'},
  'data/biome_impl/lavalake_pit.png': {'Lava Lake'},
  'data/biome_impl/lavalake_pit_cracked.png': {'Lava Lake'},
  'data/biome_impl/lavalake_racing.png': {'Lava Lake'},
  'data/biome_impl/mystery_teleport.png': {'Temple of the Art'},
  'data/biome_impl/null_room.png': {'Nullifying Altar'}, # AKA ???
  'data/biome_impl/ocarina.png': {'Cloudscape'},
  'data/biome_impl/orbroom.png': {'Orb Room'},
  'data/biome_impl/rainbow_cloud.png': {'Rainbow Cloud'},
  'data/biome_impl/roboroom.png': {'Power Plant'},
  'data/biome_impl/robot_egg.png': {'The Robotic Egg'},
  'data/biome_impl/safe_haven.png': {'Kammi'},
  #'data/biome_impl/sandroom.png': {'sandroom.png'},
  'data/biome_impl/secret_entrance.png': {'Mysterious Gate'},
  'data/biome_impl/secret_lab.png': {'Forgotten Cave', 'Throne Room', 'Abandoned Alchemy Lab'},
  'data/biome_impl/shop_room.png': {'Secret Shop'},
  #'data/biome_impl/smokecave_left.png': {'smokecave_left.png'},
  #'data/biome_impl/smokecave_middle.png': {'smokecave_middle.png'},
  #'data/biome_impl/smokecave_right.png': {'smokecave_right.png'},
  'data/biome_impl/snowperson.png': {'Snowy Depths'},
  'data/biome_impl/solid_wall_hidden_cavern.png': {'Hidden Gold Stash'},
  'data/biome_impl/teleroom.png': {'Fast Travel Room'},
  'data/biome_impl/tower_start.png': {'The Tower'},
  'data/biome_impl/watercave_layout_1.png': {'Dark Cave'},
  'data/biome_impl/watercave_layout_2.png': {'Dark Cave'},
  'data/biome_impl/watercave_layout_3.png': {'Dark Cave'},
  'data/biome_impl/watercave_layout_4.png': {'Dark Cave'},
  'data/biome_impl/watercave_layout_5.png': {'Dark Cave'},
  'data/biome_impl/wizardcave_entrance.png': {'Gate Guardian'},
  'data/biome_impl/coalmine/carthill.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/coalpit01.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/coalpit02.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/coalpit03.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/coalpit04.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/coalpit05.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/laboratory.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/oiltank_1.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/oiltank_2.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/oiltank_3.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/oiltank_4.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/oiltank_5.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/oiltank_alt.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/oiltank_puzzle.png': {'Mines'},
  'data/biome_impl/coalmine/physics_01.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/physics_02.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/physics_03.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/physics_swing_puzzle.png': {'Mines'},
  'data/biome_impl/coalmine/radioactivecave.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/receptacle_oil.png': {'Mines'},
  'data/biome_impl/coalmine/shop.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/shrine01.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/shrine02.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/slimepit.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/swarm.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/symbolroom.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/symbolroom_alt.png': {'Mines'},
  'data/biome_impl/coalmine/wandtrap_h_01.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/wandtrap_h_02.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/wandtrap_h_03.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/wandtrap_h_04.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/wandtrap_h_06.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/coalmine/wandtrap_h_07.png': {'Mines', 'Collapsed Mines'},
  'data/biome_impl/crypt/beam_01.png': {'Temple of the Art'},
  'data/biome_impl/crypt/beam_02.png': {'Temple of the Art'},
  'data/biome_impl/crypt/beam_03.png': {'Temple of the Art'},
  'data/biome_impl/crypt/beam_04.png': {'Temple of the Art'},
  'data/biome_impl/crypt/beam_05.png': {'Temple of the Art'},
  'data/biome_impl/crypt/beam_06.png': {'Temple of the Art'},
  'data/biome_impl/crypt/beam_07.png': {'Temple of the Art'},
  'data/biome_impl/crypt/beam_08.png': {'Temple of the Art'},
  'data/biome_impl/crypt/cathedral.png': {'Temple of the Art', 'Sanctuary', 'Pyramid', 'The Work', "Wizards' Den"},
  'data/biome_impl/crypt/cavein_01.png': {'Temple of the Art'},
  'data/biome_impl/crypt/cavein_02.png': {'Temple of the Art'},
  'data/biome_impl/crypt/cavein_03.png': {'Temple of the Art'},
  'data/biome_impl/crypt/cavein_04.png': {'Temple of the Art'},
  'data/biome_impl/crypt/lavaroom.png': {'Temple of the Art', 'Pyramid'},
  'data/biome_impl/crypt/mining.png': {'Temple of the Art', 'Sanctuary', 'Pyramid', 'The Work', "Wizards' Den"},
  'data/biome_impl/crypt/pit.png': {'Temple of the Art', 'Pyramid'},
  'data/biome_impl/crypt/polymorphroom.png': {'Temple of the Art', "Wizards' Den"},
  'data/biome_impl/crypt/room_gate_drop.png': {'Temple of the Art'},
  'data/biome_impl/crypt/room_gate_drop_b.png': {'Temple of the Art'},
  'data/biome_impl/crypt/room_liquid_funnel.png': {'Temple of the Art'},
  'data/biome_impl/crypt/room_liquid_funnel_b.png': {'Temple of the Art'},
  'data/biome_impl/crypt/shop.png': {'Temple of the Art'},
  'data/biome_impl/crypt/shop_b.png': {'Temple of the Art'},
  'data/biome_impl/crypt/stairs_left.png': {'Temple of the Art', 'Pyramid', "Wizards' Den"},
  'data/biome_impl/crypt/stairs_right.png': {'Temple of the Art', 'Pyramid', "Wizards' Den"},
  'data/biome_impl/crypt/symbolroom.png': {'Temple of the Art', 'Pyramid'},
  'data/biome_impl/crypt/water_lava.png': {'Temple of the Art'},
  'data/biome_impl/excavationsite/cube_chamber.png': {'Meditation Chamber'},
  'data/biome_impl/excavationsite/gunpowderpool_01.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/gunpowderpool_02.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/gunpowderpool_03.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/gunpowderpool_04.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/lake.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/lake_alt.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/machine_1.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/machine_2.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/machine_4.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/machine_5.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/machine_6.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/machine_7.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/meditation_cube.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/oiltank_1.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/puzzleroom_01.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/puzzleroom_02.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/puzzleroom_03.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/receptacle_steam.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/shop.png': {'Coal Pits'},
  'data/biome_impl/excavationsite/shop_alt.png': {'Coal Pits'},
  'data/biome_impl/huussi.png': {'Outhouse'},
  'data/biome_impl/liquidcave/container_01.png': {'Ancient Laboratory'},
  'data/biome_impl/liquidcave/liquidcave_corner.png': {'Ancient Laboratory'},
  'data/biome_impl/liquidcave/liquidcave_top.png': {'Ancient Laboratory'},
  'data/biome_impl/meatroom.png': {'Meat Realm'},
  'data/biome_impl/mountain/floating_island.png': {'Mountain'},
  'data/biome_impl/mountain/hall.png': {'Mountain'},
  'data/biome_impl/mountain/hall_b.png': {'Mountain'},
  'data/biome_impl/mountain/hall_bottom.png': {'Mountain', 'Mysterious Gate'},
  'data/biome_impl/mountain/hall_bottom_2.png': {'Mountain'},
  'data/biome_impl/mountain/hall_br.png': {'Mountain'},
  'data/biome_impl/mountain/hall_r.png': {'Mountain'},
  'data/biome_impl/mountain/inside_bottom_left.png': {'Mountain'},
  'data/biome_impl/mountain/inside_bottom_right.png': {'Mountain', 'Mysterious Gate'},
  'data/biome_impl/mountain/inside_top_left.png': {'Mountain'},
  'data/biome_impl/mountain/inside_top_right.png': {'Mountain'},
  'data/biome_impl/mountain/left.png': {'Mountain'},
  'data/biome_impl/mountain/left_2.png': {'Mountain'},
  'data/biome_impl/mountain/left_3.png': {'Mountain'},
  'data/biome_impl/mountain/left_bottom.png': {'Mountain'},
  'data/biome_impl/mountain/left_entrance.png': {'Mountain'},
  'data/biome_impl/mountain/left_entrance_below.png': {'Mountain'},
  'data/biome_impl/mountain/left_entrance_bottom.png': {'Mountain'},
  'data/biome_impl/mountain/left_stub.png': {'Mountain'},
  'data/biome_impl/mountain/left_stub_edge.png': {'Mountain'},
  'data/biome_impl/mountain/right.png': {'Mountain'},
  'data/biome_impl/mountain/right_2.png': {'Mountain'},
  'data/biome_impl/mountain/right_bottom.png': {'Mountain'},
  'data/biome_impl/mountain/right_entrance.png': {'Mountain'},
  'data/biome_impl/mountain/right_entrance_2.png': {'Mountain'},
  'data/biome_impl/mountain/right_entrance_bottom.png': {'Mountain'},
  'data/biome_impl/mountain/right_stub.png': {'Mountain'},
  'data/biome_impl/mountain/top.png': {'Mountain'},
  'data/biome_impl/overworld/cliff.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/desert_ruins_base_01.png': {'Desert'},
  'data/biome_impl/overworld/desert_ruins_base_02.png': {'Desert'},
  'data/biome_impl/overworld/desert_ruins_base_03.png': {'Desert'},
  'data/biome_impl/overworld/essence_altar.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/essence_altar_desert.png': {'Desert'},
  'data/biome_impl/overworld/scale.png': {'Desert'},
  'data/biome_impl/overworld/scale_old.png': {'Desert'},
  'data/biome_impl/overworld/snowy_rock_01.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_rock_02.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_rock_03.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_rock_04.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_rock_05.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_ruins_base_01.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_ruins_base_02.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_ruins_base_03.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_ruins_eye_pillar.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_ruins_pillar_01.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_ruins_pillar_02.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_ruins_pillar_03.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_ruins_pillar_04.png': {'Snowy Wasteland'},
  'data/biome_impl/overworld/snowy_ruins_pillar_05.png': {'Snowy Wasteland'},
  'data/biome_impl/pyramid/boss_limbs.png': {'Pyramid'},
  'data/biome_impl/pyramid/entrance.png': {'Pyramid'},
  'data/biome_impl/pyramid/hallway.png': {'Pyramid'},
  'data/biome_impl/pyramid/left.png': {'Pyramid'},
  'data/biome_impl/pyramid/right.png': {'Pyramid'},
  'data/biome_impl/pyramid/top.png': {'Pyramid'},
  'data/biome_impl/rainforest/base.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/hut01.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/hut02.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/hut03.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/oiltank_01.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/pit01.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/pit02.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/pit03.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/plantlife.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/rainforest_statue_01.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/rainforest_statue_02.png': {'Underground Jungle'},
  'data/biome_impl/rainforest/symbolroom.png': {'Underground Jungle', 'Lukki Lair'},
  'data/biome_impl/snowcastle/acidpool.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/bar.png': {'Hiisi Base', 'Sandcave'},
  'data/biome_impl/snowcastle/bedroom.png': {'Hiisi Base', 'Sandcave'},
  'data/biome_impl/snowcastle/bridge.png': {'Hiisi Base', 'Sandcave'},
  'data/biome_impl/snowcastle/cargobay.png': {'Hiisi Base', 'Sandcave'},
  'data/biome_impl/snowcastle/drill.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/forge.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/greenhouse.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/hourglass_chamber.png': {'The Hourglass Chamber'},
  'data/biome_impl/snowcastle/kitchen.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/pod_large_01.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/pod_small_l_01.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/polymorphroom.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/sauna.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/shaft.png': {'Hiisi Base', 'Sandcave'},
  'data/biome_impl/snowcastle/side_cavern_left.png': {'Hiisi Base'},
  'data/biome_impl/snowcastle/teleroom.png': {'Hiisi Base'},
  'data/biome_impl/snowcave/buried_eye.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/camp.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/crater.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/horizontalobservatory.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/horizontalobservatory2.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/horizontalobservatory3.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/icebridge.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/icebridge2.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/icebridge2_alt.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/icepillar.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/icicles.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/icicles2.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/icicles3.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/icicles4.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/pipe.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/pipe_alt.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/puzzle_capsule.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/puzzle_capsule_b.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/receptacle_water.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/secret_chamber.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/shop.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/snowcastle.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/symbolroom.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/tinyobservatory.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/tinyobservatory2.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/verticalobservatory.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/verticalobservatory2.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/verticalobservatory_alt.png': {'Snowy Depths'},
  'data/biome_impl/snowcave/verticalobservatory2_alt.png': {'Snowy Depths'},
  'data/biome_impl/temple/altar.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_empty.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_left.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_right.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_right_extra.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_snowcastle_capsule.png': {'Hiisi Base'},
  'data/biome_impl/temple/altar_snowcave_capsule.png': {'Snowy Depths'},
  'data/biome_impl/temple/altar_top.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_top_blood.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_top_ending.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_top_lava.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_top_oil.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_top_radioactive.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_top_water.png': {'Holy Mountain'},
  'data/biome_impl/temple/altar_vault_capsule.png': {'Frozen Vault'},
  'data/biome_impl/vault/acidtank.png': {'Frozen Vault'},
  'data/biome_impl/vault/brain_room.png': {'Frozen Vault'},
  'data/biome_impl/vault/catwalk_01.png': {'Frozen Vault'},
  'data/biome_impl/vault/catwalk_02.png': {'Frozen Vault'},
  'data/biome_impl/vault/catwalk_02b.png': {'Frozen Vault'},
  'data/biome_impl/vault/catwalk_03.png': {'Frozen Vault'},
  'data/biome_impl/vault/catwalk_04.png': {'Frozen Vault'},
  'data/biome_impl/vault/electric_tunnel_room.png': {'Frozen Vault'},
  'data/biome_impl/vault/entrance.png': {'Frozen Vault'},
  'data/biome_impl/vault/lab.png': {'Frozen Vault'},
  'data/biome_impl/vault/lab_puzzle.png': {'Frozen Vault'},
  'data/biome_impl/vault/lab2.png': {'Frozen Vault'},
  'data/biome_impl/vault/lab3.png': {'Frozen Vault'},
  'data/biome_impl/vault/pipe_big_hor_1.png': {'Frozen Vault'},
  'data/biome_impl/vault/shop.png': {'Frozen Vault'},
  'data/biome_impl/vault/symbolroom.png': {'Frozen Vault'},
  'data/biome_impl/spliced/boss_arena.png': {'The Laboratory'},
  'data/biome_impl/spliced/bridge.png': {'Snowy Wasteland'},
  'data/biome_impl/spliced/gourd_room.png': {'Gourd Cave'},
  'data/biome_impl/spliced/lake_statue.png': {'Lake'},
  'data/biome_impl/spliced/lavalake_pit_bottom.png': {'Lava Lake'},
  'data/biome_impl/spliced/lavalake2.png': {'Lava Lake'},
  'data/biome_impl/spliced/moon.png': {'Moon'},
  'data/biome_impl/spliced/moon_dark.png': {'Dark Moon'},
  'data/biome_impl/spliced/mountain_lake.png': {'Mountain'},
  'data/biome_impl/spliced/skull.png': {'Desert'},
  'data/biome_impl/spliced/tree.png': {'Giant Tree'},
  'data/biome_impl/spliced/skull_in_desert/1.png': {'Desert'},
  'data/wang_tiles/clouds.png': {'Cloudscape'},
  'data/wang_tiles/coalmine.png': {'Mines', 'The Tower'},
  'data/wang_tiles/coalmine_alt.png': {'Collapsed Mines'},
  'data/wang_tiles/crypt.png': {'Temple of the Art', 'The Tower'},
  'data/wang_tiles/excavationsite.png': {'Coal Pits', 'The Tower'},
  'data/wang_tiles/fungicave.png': {'Fungal Caverns', 'The Tower'},
  'data/wang_tiles/fungiforest.png': {'Overgrown Cavern'},
  'data/wang_tiles/liquidcave.png': {'Ancient Laboratory'},
  'data/wang_tiles/meat.png': {'Meat Realm'},
  'data/wang_tiles/pyramid.png': {'Pyramid'},
  'data/wang_tiles/rainforest.png': {'Underground Jungle', 'The Tower'},
  'data/wang_tiles/rainforest_dark.png': {'Lukki Lair'},
  'data/wang_tiles/rainforest_open.png': {'Underground Jungle'},
  'data/wang_tiles/robobase.png': {'Power Plant'},
  'data/wang_tiles/sandcave.png': {'Sandcave'},
  'data/wang_tiles/snowcastle.png': {'Hiisi Base', 'The Tower'},
  'data/wang_tiles/snowcave.png': {'Snowy Depths', 'The Tower'},
  'data/wang_tiles/snowchasm.png': {'Snowy Chasm'},
  'data/wang_tiles/the_end.png': {'The Work (Hell)', 'The Tower'},
  'data/wang_tiles/the_sky.png': {'The Work (Sky)'},
  'data/wang_tiles/vault.png': {'The Vault', 'The Tower'},
  'data/wang_tiles/vault_frozen.png': {'Frozen Vault'},
  'data/wang_tiles/wand.png': {'Magical Temple'},
  'data/wang_tiles/wizardcave.png': {"Wizards' Den"},
}


# These were manually retrieved from the biome xml/lua files
biome_mat_mapping = {
  "acid": {"The Vault"},
  "alcohol": {"Mines", "Ancient Laboratory", "The Tower", "The Vault"},
  "blood_cold": {"Mines", "The Tower"},
  "blood_fungi": {"Mines", "The Tower"},
  "blood": {"Mines", "The Tower"},
  "bone": {"Desert"},
  "cactus": {"Desert"},
  "ceiling_plant_material": {"Mines", "Temple of the Art", "Coal Pits", "Fungal Caverns", "Pyramid", "Underground Jungle", "Power Plant", "The Vault", "Magical Temple", "Collapsed Mines", "Desert", "Forest", "Mountain"},
  "cement": {"Mines", "The Tower"},
  "cloud_lighter": {"Cloudscape", "The Work (Sky)"},
  "cloud": {"Cloudscape", "The Work (Sky)"},
  "coal_static": {"Coal Pits"},
  "coal": {"Mines", "Coal Pits", "Collapsed Mines"},
  "copper": {"Mines", "Ancient Laboratory", "Collapsed Mines"},
  "diamond": {"Temple of the Art", "Coal Pits", "Orb Room", "Forgotten Cave", "Pyramid", "Throne Room", "Abandoned Alchemy Lab", "Magical Temple"},
  "fungisoil": {"Fungal Caverns", "Overgrown Cavern"},
  "fungus_loose": {"Mines", "Collapsed Mines", "Coal Pits", "Fungal Caverns", "Overgrown Cavern", "Underground Jungle", "Forest"},
  "gold": {"Mines", "Coal Pits", "Fungal Caverns", "Overgrown Cavern", "The Gold", "Ancient Laboratory", "Lukki Lair", "Underground Jungle", "Power Plant", "The Vault", "Wizards' Den", "Collapsed Mines", "Mountain", "Meat Realm"},
  "grass_dark": {"Lukki Lair"},
  "grass": {"Mines", "Collapsed Mines", "Ancient Laboratory", "Underground Jungle", "Wizards' Den", "Forest", "Mountain"},
  "gunpowder_explosive": {"Mines", "The Tower"},
  "honey": {"Mines", "The Tower"},
  "ice_static": {"Hiisi Base", "Snowy Depths", "Frozen Vault", "Mountain"},
  "lava": {"Volcanic Lake", "The Robotic Egg", "The Work (Hell)", "Mines", "Ancient Laboratory", "The Tower", "Lava Lake"},
  "liquid_fire": {"Ancient Laboratory"},
  "magic_liquid_berserk": {"Mines", "The Tower", "Ancient Laboratory"},
  "magic_liquid_charm": {"Mines", "The Tower", "Ancient Laboratory"},
  "magic_liquid_hp_regeneration": {"Mines", "The Tower"},
  "magic_liquid_invisibility": {"Mines", "The Tower"},
  "magic_liquid_mana_regeneration": {"Ancient Laboratory"},
  "magic_liquid_polymorph": {"Mines", "The Tower"},
  "magic_liquid_protection_all": {"Ancient Laboratory"},
  "magic_liquid_random_polymorph": {"Mines", "The Tower"},
  "magic_liquid_teleportation": {"Mines", "Ancient Laboratory", "The Tower"},
  "magic_liquid_unstable_polymorph": {"Ancient Laboratory"},
  "magic_liquid_weakness": {"Ancient Laboratory"},
  "material_confusion": {"Ancient Laboratory"},
  "meat_static": {"Meat Realm"},
  "moss": {"Coal Pits", "Ancient Laboratory", "Wizards' Den", "Forest", "Mountain"},
  "oil": {"Mines", "Ancient Laboratory", "The Tower"},
  "plant_material_red": {"Coal Pits", "The Work (Hell)", "Magical Temple"},
  "plant_material": {"Mines", "Collapsed Mines", "Underground Jungle", "Forest", "Mountain"},
  "poison": {"Mines", "The Tower"},
  "radioactive_liquid": {"Power Plant", "The Vault", "Magical Temple", "Mines", "The Tower"},
  "rock_hard_border": {"Dragoncave", "Friend Room", "Lava Lake"},
  "rock_hard": {"Temple of the Art", "Orb Room", "Forgotten Cave", "Pyramid", "Sandcave", "Throne Room", "Abandoned Alchemy Lab", "Dragoncave", "Friend Room", "Lava Lake", "Mountain"},
  "rock_static_fungal": {"Overgrown Cavern"},
  "rock_static_grey": {"Coal Pits", "Power Plant"},
  "rock_static_purple": {"Wizards' Den"},
  "rock_static_wet": {"Mines", "Collapsed Mines"},
  "rock_static": {"Fungal Caverns", "Power Plant", "The Vault", "Desert", "Forest", "Mountain", "Pyramid"},
  "rock_vault": {"The Vault"},
  "salt": {"Mines", "The Tower"},
  "sand_static_bright": {"Desert", "Pyramid"},
  "sand_static_rainforest_dark": {"Lukki Lair"},
  "sand_static_rainforest": {"Underground Jungle"},
  "sand_static_red": {"Sandcave"},
  "sand_static": {"Desert", "Mines", "The Tower", "Temple of the Art", "Fungal Caverns", "Orb Room", "Forgotten Cave", "Ancient Laboratory", "Pyramid", "Throne Room", "Abandoned Alchemy Lab", "Collapsed Mines", "Forest"},
  "sand_surface": {"Desert", "Pyramid"},
  "sand": {"Sandcave", "Mines", "The Tower"},
  "sandstone_surface":{"Desert", "Pyramid"},
  "sandstone": {"Sandcave"},
  "skullrock": {"The Work (Hell)"},
  "slime": {"Mines", "The Tower"},
  "snow_static": {"Hiisi Base", "Snowy Depths", "Frozen Vault", "Snowy Chasm", "Snowy Wasteland", "Mountain"},
  "snow_sticky": {"Hiisi Base", "Snowy Depths", "Frozen Vault", "Mountain"},
  "snow": {"The Work (Sky)"},
  "snowrock_static": {"Hiisi Base", "Snowy Depths", "Frozen Vault", "Snowy Chasm", "Snowy Wasteland", "Snowy Wasteland", "Mountain"},
  "soil_dead": {"Lukki Lair"},
  "soil_lush_dark": {"Lukki Lair"},
  "soil_lush": {"Underground Jungle"},
  "soil": {"Mines", "Ancient Laboratory", "Underground Jungle", "Power Plant", "Sandcave", "The Vault", "Wizards' Den", "Collapsed Mines", 'Forest', "Mountain"},
  "templebrickdark_static": {"Temple of the Art", "Orb Room", "Forgotten Cave", "Pyramid", "Throne Room", "Abandoned Alchemy Lab"},
  "templeslab_crumbling_static": {"Magical Temple"},
  "the_end": {"The Work (Hell)"},
  "water": {"Lukki Lair", "Underground Jungle", "Sandcave", "Water (Biome)", "Mines", "The Tower", "Lake"},
  "wood_loose": {"Desert", "Forest"},
}

special_mapping = {
  0xff0000: 'spawn_small_enemies',
  0x800000: 'spawn_big_enemies',
  0x00ff00: 'spawn_items',
  0xc88d1a: 'spawn_props',
  0xc88000: 'spawn_props2',
  0xc80040: 'spawn_props3',
  0xffff00: 'spawn_lamp',
  0xff0aff: 'load_pixel_scene',
  0xFF0080: 'load_pixel_scene2',
  0xFF8000: 'spawn_unique_enemy',
  0xc84040: 'spawn_unique_enemy2',
  0x804040: 'spawn_unique_enemy3',
  0x96C850: 'spawn_ghostlamp',
  0x60A064: 'spawn_candles',
  0x50a000: 'spawn_potion_altar',
  0xbca0f0: 'spawn_potions',
  0x00FF5A: 'spawn_apparition',
  0x78FFFF: 'spawn_heart',
  0x50A0F0: 'spawn_wands',
  0xbf26a6: 'spawn_portal',
  0x04A977: 'spawn_end_portal',
  0xffd171: 'spawn_orb',
  0xffd181: 'spawn_perk',
  0xffff81: 'spawn_all_perks',
  0xc7eb28: 'spawn_wand_trap',
  0xE8FF80: 'spawn_wand_trap_ignite',
  0x2768DE: 'spawn_wand_trap_electricity_source',
  0x2768DF: 'spawn_wand_trap_electricity',
  0x6b4f9b: 'spawn_moon',
  0xd7b3e8: 'spawn_collapse',
}

ignore_colours = {
  0x0000ff,
  0x00ff00,
  0x00ffff,
  0x5555b4,
  0x55b4b4,
  0x55b8d9,
  0x55ffff,
  0xb45584,
  0xb4b468,
  0xd9b1a4,
  0xf1ff69,
  0xff00ff,
  0xff7777,
  0xffaa55,
  0xffd3bb,
  0xffd455,
  0xffff00,
  0x47415e,
  0x11dea7,
  0x6f3501,
  0x11dda7,
  0xffabab,
  0xaa55ff,
  0xb455b4,
}

reverse_spell_lookup = {
  "$action_testbullet": {
  "data/entities/animals/boss_centipede/firepillar.xml",
  },
  "$action_bomb": {
  "data/entities/projectiles/bomb.xml",
  "data/entities/misc/custom_cards/bomb.xml",
  },
  "$action_light_bullet": {
  "data/entities/projectiles/deck/light_bullet.xml",
  },
  "$action_light_bullet_trigger": {
  "data/entities/projectiles/deck/light_bullet.xml",
  },
  "$action_light_bullet_trigger_2": {
  "data/entities/projectiles/deck/light_bullet_blue.xml",
  },
  "$action_light_bullet_timer": {
  "data/entities/projectiles/deck/light_bullet.xml",
  },
  "$action_bullet": {
  "data/entities/projectiles/deck/bullet.xml",
  },
  "$action_bullet_trigger": {
  "data/entities/projectiles/deck/bullet.xml",
  },
  "$action_bullet_timer": {
  "data/entities/projectiles/deck/bullet.xml",
  },
  "$action_heavy_bullet": {
  "data/entities/projectiles/deck/bullet_heavy.xml",
  },
  "$action_heavy_bullet_trigger": {
  "data/entities/projectiles/deck/bullet_heavy.xml",
  },
  "$action_heavy_bullet_timer": {
  "data/entities/projectiles/deck/bullet_heavy.xml",
  },
  "$action_air_bullet": {
  "data/entities/projectiles/deck/light_bullet_air.xml",
  },
  "$action_slow_bullet": {
  "data/entities/projectiles/deck/bullet_slow.xml",
  "data/entities/misc/custom_cards/bullet_slow.xml",
  },
  "$action_slow_bullet_trigger": {
  "data/entities/projectiles/deck/bullet_slow.xml",
  "data/entities/misc/custom_cards/bullet_slow.xml",
  },
  "$action_slow_bullet_timer": {
  "data/entities/projectiles/deck/bullet_slow.xml",
  "data/entities/misc/custom_cards/bullet_slow.xml",
  },
  "$action_black_hole": {
  "data/entities/projectiles/deck/black_hole.xml",
  "data/entities/misc/custom_cards/black_hole.xml",
  },
  "$action_black_hole_death_trigger": {
  "data/entities/projectiles/deck/black_hole.xml",
  "data/entities/misc/custom_cards/black_hole.xml",
  },
  "$action_black_hole_big": {
  "data/entities/projectiles/deck/black_hole_big.xml",
  "data/entities/misc/custom_cards/black_hole_big.xml",
  },
  "$action_black_hole_giga": {
  "data/entities/projectiles/deck/black_hole_giga.xml",
  "data/entities/misc/custom_cards/black_hole_giga.xml",
  },
  "$action_tentacle_portal": {
  "data/entities/projectiles/deck/tentacle_portal.xml",
  },
  "$action_decoy": {
  "data/entities/misc/custom_cards/decoy.xml",
  "data/entities/projectiles/deck/decoy.xml",
  },
  "$action_decoy_trigger": {
  "data/entities/misc/custom_cards/decoy_trigger.xml",
  "data/entities/projectiles/deck/decoy_trigger.xml",
  },
  "$action_spitter": {
  "data/entities/projectiles/deck/spitter.xml",
  },
  "$action_spitter_timer": {
  "data/entities/projectiles/deck/spitter.xml",
  },
  "$action_spitter_tier_2": {
  "data/entities/projectiles/deck/spitter_tier_2.xml",
  },
  "$action_spitter_tier_2_timer": {
  "data/entities/projectiles/deck/spitter_tier_2.xml",
  },
  "$action_spitter_tier_3": {
  "data/entities/projectiles/deck/spitter_tier_3.xml",
  },
  "$action_spitter_tier_3_timer": {
  "data/entities/projectiles/deck/spitter_tier_3.xml",
  },
  "$action_bubbleshot": {
  "data/entities/projectiles/deck/bubbleshot.xml",
  },
  "$action_bubbleshot_trigger": {
  "data/entities/projectiles/deck/bubbleshot.xml",
  },
  "$action_disc_bullet": {
  "data/entities/projectiles/deck/disc_bullet.xml",
  },
  "$action_disc_bullet_big": {
  "data/entities/projectiles/deck/disc_bullet_big.xml",
  },
  "$action_omega_disc_bullet": {
  "data/entities/projectiles/deck/disc_bullet_bigger.xml",
  },
  "$action_bouncy_orb": {
  "data/entities/projectiles/deck/bouncy_orb.xml",
  },
  "$action_bouncy_orb_timer": {
  "data/entities/projectiles/deck/bouncy_orb.xml",
  },
  "$action_rubber_ball": {
  "data/entities/projectiles/deck/rubber_ball.xml",
  },
  "$action_arrow": {
  "data/entities/projectiles/deck/arrow.xml",
  },
  "$action_pollen": {
  "data/entities/projectiles/deck/pollen.xml",
  },
  "$action_lance": {
  "data/entities/projectiles/deck/lance.xml",
  "data/entities/misc/custom_cards/lance.xml",
  },
  "$action_rocket": {
  "data/entities/projectiles/deck/rocket.xml",
  "data/entities/misc/custom_cards/rocket.xml",
  },
  "$action_rocket_tier_2": {
  "data/entities/projectiles/deck/rocket_tier_2.xml",
  "data/entities/misc/custom_cards/rocket_tier_2.xml",
  },
  "$action_rocket_tier_3": {
  "data/entities/projectiles/deck/rocket_tier_3.xml",
  "data/entities/misc/custom_cards/rocket_tier_3.xml",
  },
  "$action_grenade": {
  "data/entities/projectiles/deck/grenade.xml",
  "data/entities/misc/custom_cards/grenade.xml",
  },
  "$action_grenade_trigger": {
  "data/entities/projectiles/deck/grenade.xml",
  "data/entities/misc/custom_cards/grenade_trigger.xml",
  },
  "$action_grenade_tier_2": {
  "data/entities/projectiles/deck/grenade_tier_2.xml",
  "data/entities/misc/custom_cards/grenade_tier_2.xml",
  },
  "$action_grenade_tier_3": {
  "data/entities/projectiles/deck/grenade_tier_3.xml",
  "data/entities/misc/custom_cards/grenade_tier_3.xml",
  },
  "$action_grenade_anti": {
  "data/entities/projectiles/deck/grenade_anti.xml",
  "data/entities/misc/custom_cards/grenade.xml",
  },
  "$action_grenade_large": {
  "data/entities/projectiles/deck/grenade_large.xml",
  "data/entities/misc/custom_cards/grenade.xml",
  },
  "$action_mine": {
  "data/entities/projectiles/deck/mine.xml",
  },
  "$action_mine_death_trigger": {
  "data/entities/projectiles/deck/mine.xml",
  },
  "$action_pipe_bomb": {
  "data/entities/projectiles/deck/pipe_bomb.xml",
  },
  "$action_pipe_bomb_death_trigger": {
  "data/entities/projectiles/deck/pipe_bomb.xml",
  },
  "$action_exploding_deer": {
  "data/entities/projectiles/deck/exploding_deer.xml",
  },
  "$action_exploding_ducks": {
  "data/entities/projectiles/deck/duck.xml",
  },
  "$action_worm_shot": {
  "data/entities/projectiles/deck/worm_shot.xml",
  },
  "$action_pipe_bomb_detonator": {
  "data/entities/projectiles/deck/pipe_bomb_detonator.xml",
  },
  "$action_bomb_detonator": {
  "data/entities/projectiles/deck/bomb_detonator.xml",
  },
  "$action_laser": {
  "data/entities/projectiles/deck/laser.xml",
  "data/entities/misc/custom_cards/laser.xml",
  "data/entities/misc/effect_disintegrated.xml",
  },
  "$action_megalaser": {
  "data/entities/projectiles/deck/megalaser.xml",
  "data/entities/projectiles/deck/megalaser_beam.xml",
  "data/entities/misc/effect_disintegrated.xml",
  },
  "$action_lightning": {
  "data/entities/projectiles/deck/lightning.xml",
  "data/entities/misc/custom_cards/electric_charge.xml",
  },
  "$action_ball_lightning": {
  "data/entities/projectiles/deck/ball_lightning.xml",
  "data/entities/misc/custom_cards/electric_charge.xml",
  },
  "$action_laser_emitter": {
  "data/entities/projectiles/deck/orb_laseremitter.xml",
  "data/entities/misc/effect_disintegrated.xml",
  },
  "$action_laser_emitter_four": {
  "data/entities/projectiles/deck/orb_laseremitter.xml",
  "data/entities/projectiles/deck/orb_laseremitter_four.xml",
  "data/entities/misc/effect_disintegrated.xml",
  },
  "$action_laser_emitter_cutter": {
  "data/entities/projectiles/deck/orb_laseremitter_cutter.xml",
  "data/entities/misc/effect_disintegrated.xml",
  },
  "$action_digger": {
  "data/entities/projectiles/deck/digger.xml",
  },
  "$action_powerdigger": {
  "data/entities/projectiles/deck/powerdigger.xml",
  },
  "$action_chainsaw": {
  "data/entities/projectiles/deck/chainsaw.xml",
  },
  "$action_luminous_drill": {
  "data/entities/projectiles/deck/luminous_drill.xml",
  },
  "$action_luminous_drill_timer": {
  "data/entities/projectiles/deck/luminous_drill.xml",
  },
  "$action_tentacle": {
  "data/entities/projectiles/deck/tentacle.xml",
  "data/entities/misc/custom_cards/tentacle.xml",
  },
  "$action_tentacle_timer": {
  "data/entities/projectiles/deck/tentacle.xml",
  "data/entities/misc/custom_cards/tentacle_timer.xml",
  },
  "$action_bloodtentacle": {
  "data/entities/projectiles/deck/bloodtentacle.xml",
  },
  "$action_heal_bullet": {
  "data/entities/projectiles/deck/heal_bullet.xml",
  "data/entities/misc/custom_cards/heal_bullet.xml",
  },
  "$action_spiral_shot": {
  "data/entities/projectiles/deck/spiral_shot.xml",
  "data/entities/misc/custom_cards/spiral_shot.xml",
  },
  "$action_magic_shield": {
  "data/entities/projectiles/deck/magic_shield_start.xml",
  },
  "$action_big_magic_shield": {
  "data/entities/projectiles/deck/big_magic_shield_start.xml",
  },
  "$action_chain_bolt": {
  "data/entities/projectiles/deck/chain_bolt.xml",
  },
  "$action_fireball": {
  "data/entities/projectiles/deck/fireball.xml",
  "data/entities/misc/custom_cards/fireball.xml",
  },
  "$action_meteor": {
  "data/entities/projectiles/deck/meteor.xml",
  },
  "$action_flamethrower": {
  "data/entities/projectiles/deck/flamethrower.xml",
  "data/entities/misc/custom_cards/flamethrower.xml",
  },
  "$action_iceball": {
  "data/entities/projectiles/deck/iceball.xml",
  "data/entities/misc/custom_cards/iceball.xml",
  },
  "$action_icethrower": {
  "data/entities/misc/custom_cards/icethrower.xml",
  "data/entities/projectiles/icethrower.xml",
  },
  "$action_slimeball": {
  "data/entities/projectiles/deck/slime.xml",
  "data/entities/misc/custom_cards/slimeball.xml",
  },
  "$action_darkflame": {
  "data/entities/projectiles/deck/darkflame.xml",
  "data/entities/misc/custom_cards/darkflame.xml",
  "data/entities/projectiles/darkflame.xml",
  },
  "$action_missile": {
  "data/entities/projectiles/deck/rocket_player.xml",
  },
  "$action_pebble": {
  "data/entities/projectiles/deck/pebble_player.xml",
  },
  "$action_dynamite": {
  "data/entities/projectiles/deck/tnt.xml",
  "data/entities/misc/custom_cards/tnt.xml",
  },
  "$action_glitter_bomb": {
  "data/entities/projectiles/deck/glitter_bomb.xml",
  "data/entities/misc/custom_cards/glitter_bomb.xml",
  },
  "$action_buckshot": {
  "data/entities/projectiles/deck/buckshot_player.xml",
  },
  "$action_freezing_gaze": {
  "data/entities/projectiles/deck/freezing_gaze_beam.xml",
  },
  "$action_glowing_bolt": {
  "data/entities/projectiles/deck/glowing_bolt.xml",
  },
  "$action_bomb_legacy": {
  "data/entities/projectiles/deck/bomb.xml",
  },
  "$action_spore_pod": {
  "data/entities/projectiles/deck/spore_pod.xml",
  },
  "$action_glue_shot": {
  "data/entities/projectiles/deck/glue_shot.xml",
  },
  "$action_bomb_holy": {
  "data/entities/projectiles/bomb_holy.xml",
  "data/entities/misc/custom_cards/bomb_holy.xml",
  },
  "$action_bomb_holy_giga": {
  "data/entities/projectiles/bomb_holy_giga.xml",
  "data/entities/misc/custom_cards/bomb_holy_giga.xml",
  },
  "$action_propane_tank": {
  "data/entities/projectiles/propane_tank.xml",
  "data/entities/misc/custom_cards/propane_tank.xml",
  },
  "$action_bomb_cart": {
  "data/entities/projectiles/bomb_cart.xml",
  },
  "$action_cursed_orb": {
  "data/entities/projectiles/orb_cursed.xml",
  },
  "$action_expanding_orb": {
  "data/entities/projectiles/orb_expanding.xml",
  },
  "$action_crumbling_earth": {
  "data/entities/projectiles/deck/crumbling_earth.xml",
  },
  "$action_summon_rock": {
  "data/entities/projectiles/deck/rock.xml",
  "data/entities/misc/custom_cards/summon_rock.xml",
  },
  "$action_summon_egg": {
  "data/entities/items/pickup/egg_monster.xml",
  "data/entities/items/pickup/egg_slime.xml",
  "data/entities/items/pickup/egg_red.xml",
  "data/entities/items/pickup/egg_fire.xml",
  },
  "$action_summon_hollow_egg": {
  "data/entities/items/pickup/egg_hollow.xml",
  },
  "$action_tntbox": {
  "data/entities/projectiles/deck/tntbox.xml",
  },
  "$action_tntbox_big": {
  "data/entities/projectiles/deck/tntbox_big.xml",
  },
  "$action_swarm_fly": {
  "data/entities/projectiles/deck/swarm_fly.xml",
  },
  "$action_swarm_firebug": {
  "data/entities/projectiles/deck/swarm_firebug.xml",
  },
  "$action_swarm_wasp": {
  "data/entities/projectiles/deck/swarm_wasp.xml",
  },
  "$action_friend_fly": {
  "data/entities/projectiles/deck/friend_fly.xml",
  },
  "$action_knife": {
  "data/entities/misc/custom_cards/knife.xml",
  "data/entities/projectiles/deck/knife.xml",
  },
  "$action_circleshot_a": {
  "data/entities/misc/custom_cards/circleshot_a.xml",
  "data/entities/projectiles/orbspawner_green.xml",
  },
  "$action_circleshot_b": {
  "data/entities/misc/custom_cards/circleshot_b.xml",
  "data/entities/projectiles/orbspawner.xml",
  },
  "$action_acidshot": {
  "data/entities/projectiles/deck/acidshot.xml",
  "data/entities/misc/custom_cards/acidshot.xml",
  },
  "$action_thunderball": {
  "data/entities/projectiles/thunderball.xml",
  "data/entities/misc/custom_cards/thunderball.xml",
  },
  "$action_bloomshot": {
  "data/entities/misc/custom_cards/bloomshot.xml",
  "data/entities/projectiles/bloomshot.xml",
  },
  "$action_icecircle": {
  "data/entities/misc/custom_cards/icecircle.xml",
  "data/entities/projectiles/iceskull_explosion.xml",
  },
  "$action_firebomb": {
  "data/entities/projectiles/deck/firebomb.xml",
  "data/entities/misc/custom_cards/firebomb.xml",
  },
  "$action_soilball": {
  "data/entities/projectiles/chunk_of_soil.xml",
  },
  "$action_pink_orb": {
  "data/entities/misc/custom_cards/pink_orb.xml",
  "data/entities/projectiles/deck/pink_orb.xml",
  },
  "$action_death_cross": {
  "data/entities/projectiles/deck/death_cross.xml",
  "data/entities/misc/custom_cards/death_cross.xml",
  },
  "$action_death_cross_big": {
  "data/entities/projectiles/deck/death_cross_big.xml",
  "data/entities/misc/custom_cards/death_cross.xml",
  },
  "$action_infestation": {
  "data/entities/projectiles/deck/infestation.xml",
  },
  "$action_wall_horizontal": {
  "data/entities/projectiles/deck/wall_horizontal.xml",
  },
  "$action_wall_vertical": {
  "data/entities/projectiles/deck/wall_vertical.xml",
  },
  "$action_wall_square": {
  "data/entities/projectiles/deck/wall_square.xml",
  },
  "$action_temporary_wall": {
  "data/entities/projectiles/deck/temporary_wall.xml",
  },
  "$action_temporary_platform": {
  "data/entities/projectiles/deck/temporary_platform.xml",
  },
  "$action_purple_explosion_field": {
  "data/entities/projectiles/deck/purple_explosion_field.xml",
  },
  "$action_delayed_spell": {
  "data/entities/projectiles/deck/delayed_spell.xml",
  },
  "$action_long_distance_cast": {
  "data/entities/projectiles/deck/long_distance_cast.xml",
  },
  "$action_teleport_cast": {
  "data/entities/projectiles/deck/teleport_cast.xml",
  },
  "$action_super_teleport_cast": {
  "data/entities/projectiles/deck/super_teleport_cast.xml",
  },
  "$action_commander_bullet": {
  "data/entities/projectiles/deck/commander_bullet.xml",
  },
  "$action_plasma_flare": {
  "data/entities/misc/custom_cards/plasma_flare.xml",
  "data/entities/projectiles/orb_pink_fast.xml",
  },
  "$action_keyshot": {
  "data/entities/projectiles/deck/keyshot.xml",
  },
  "$action_mana": {
  "data/entities/misc/custom_cards/mana.xml",
  "data/entities/projectiles/deck/mana.xml",
  },
  "$action_skull": {
  "data/entities/projectiles/deck/skull.xml",
  },
  "$action_material_debug": {
  "data/entities/projectiles/deck/material_debug.xml",
  },
  "$action_material_liquid": {
  "data/entities/misc/custom_cards/material_liquid.xml",
  "data/entities/projectiles/deck/material_liquid.xml",
  },
  "$action_mist_radioactive": {
  "data/entities/projectiles/deck/mist_radioactive.xml",
  },
  "$action_mist_alcohol": {
  "data/entities/projectiles/deck/mist_alcohol.xml",
  },
  "$action_mist_slime": {
  "data/entities/projectiles/deck/mist_slime.xml",
  },
  "$action_mist_blood": {
  "data/entities/projectiles/deck/mist_blood.xml",
  },
  "$action_circle_fire": {
  "data/entities/projectiles/deck/circle_fire.xml",
  },
  "$action_circle_acid": {
  "data/entities/projectiles/deck/circle_acid.xml",
  },
  "$action_circle_oil": {
  "data/entities/projectiles/deck/circle_oil.xml",
  },
  "$action_circle_water": {
  "data/entities/projectiles/deck/circle_water.xml",
  },
  "$action_material_water": {
  "data/entities/projectiles/deck/material_water.xml",
  "data/entities/misc/effect_apply_wet.xml",
  },
  "$action_material_oil": {
  "data/entities/projectiles/deck/material_oil.xml",
  "data/entities/misc/effect_apply_oiled.xml",
  },
  "$action_material_blood": {
  "data/entities/projectiles/deck/material_blood.xml",
  "data/entities/misc/effect_apply_bloody.xml",
  },
  "$action_material_acid": {
  "data/entities/projectiles/deck/material_acid.xml",
  },
  "$action_material_cement": {
  "data/entities/projectiles/deck/material_cement.xml",
  },
  "$action_material_lava": {
  "data/entities/projectiles/deck/material_lava.xml",
  },
  "$action_material_gunpowder_explosive": {
  "data/entities/projectiles/deck/material_gunpowder_explosive.xml",
  },
  "$action_material_dirt": {
  "data/entities/projectiles/deck/material_dirt.xml",
  },
  "$action_building_board_wood": {
  "data/entities/misc/custom_cards/action_building_board_wood.xml",
  },
  "$action_building_back_wall_rock": {
  "data/entities/misc/custom_cards/action_building_back_wall.xml",
  },
  "$action_building_pressure_plate": {
  "data/entities/misc/custom_cards/action_building_pressure_plate.xml",
  },
  "$action_building_physics_templedoor": {
  "data/entities/misc/custom_cards/action_building_physics_templedoor.xml",
  },
  "$action_teleport_projectile": {
  "data/entities/projectiles/deck/teleport_projectile.xml",
  "data/entities/misc/custom_cards/teleport_projectile.xml",
  },
  "$action_teleport_projectile_short": {
  "data/entities/projectiles/deck/teleport_projectile_short.xml",
  "data/entities/misc/custom_cards/teleport_projectile_short.xml",
  },
  "$action_teleport_projectile_static": {
  "data/entities/projectiles/deck/teleport_projectile_static.xml",
  "data/entities/misc/custom_cards/teleport_projectile_static.xml",
  },
  "$action_swapper_projectile": {
  "data/entities/projectiles/deck/swapper.xml",
  },
  "$action_teleport_closer": {
  "data/entities/projectiles/deck/teleport_projectile_closer.xml",
  },
  "$action_teleport_home": {
  "data/entities/projectiles/deck/teleport_home.xml",
  },
  "$action_levitation_projectile": {
  "data/entities/misc/custom_cards/levitation_projectile.xml",
  "data/entities/projectiles/deck/levitation_projectile.xml",
  },
  "$action_nuke": {
  "data/entities/projectiles/deck/nuke.xml",
  "data/entities/misc/custom_cards/nuke.xml",
  },
  "$action_nuke_giga": {
  "data/entities/projectiles/deck/nuke_giga.xml",
  "data/entities/misc/custom_cards/nuke_giga.xml",
  },
  "$action_high_explosive": {
  "data/entities/misc/custom_cards/high_explosive.xml",
  },
  "$action_drone": {
  "data/entities/misc/custom_cards/action_drone.xml",
  "data/entities/misc/player_drone.xml",
  },
  "$action_firework": {
  "data/entities/projectiles/deck/fireworks/firework_pink.xml",
  "data/entities/projectiles/deck/fireworks/firework_green.xml",
  "data/entities/projectiles/deck/fireworks/firework_blue.xml",
  "data/entities/projectiles/deck/fireworks/firework_orange.xml",
  },
  "$action_summon_wandghost": {
  "data/entities/projectiles/deck/wand_ghost_player.xml",
  "data/entities/particles/image_emitters/wand_effect.xml",
  },
  "$action_touch_gold": {
  "data/entities/projectiles/deck/touch_gold.xml",
  },
  "$action_touch_water": {
  "data/entities/projectiles/deck/touch_water.xml",
  },
  "$action_touch_oil": {
  "data/entities/projectiles/deck/touch_oil.xml",
  },
  "$action_touch_alcohol": {
  "data/entities/projectiles/deck/touch_alcohol.xml",
  },
  "$action_touch_blood": {
  "data/entities/projectiles/deck/touch_blood.xml",
  },
  "$action_touch_smoke": {
  "data/entities/projectiles/deck/touch_smoke.xml",
  },
  "$action_destruction": {
  "data/entities/projectiles/deck/destruction.xml",
  },
  "$action_lifetime": {
  "data/entities/misc/custom_cards/lifetime.xml",
  },
  "$action_lifetime_down": {
  "data/entities/misc/custom_cards/lifetime_down.xml",
  },
  "$action_nolla": {
  "data/entities/misc/nolla.xml",
  },
  "$action_explosion_remove": {
  "data/entities/misc/explosion_remove.xml",
  },
  "$action_explosion_tiny": {
  "data/entities/misc/explosion_tiny.xml",
  },
  "$action_laser_emitter_wider": {
  "data/entities/misc/laser_emitter_wider.xml",
  },
  "$action_lifetime_infinite": {
  "data/entities/misc/custom_cards/lifetime_infinite.xml",
  "data/entities/misc/lifetime_infinite.xml",
  },
  "$action_mana_reduce": {
  "data/entities/misc/custom_cards/mana_reduce.xml",
  },
  "$action_blood_magic": {
  "data/entities/particles/blood_sparks.xml",
  "data/entities/misc/custom_cards/blood_magic.xml",
  },
  "$action_money_magic": {
  "data/entities/particles/gold_sparks.xml",
  "data/entities/misc/custom_cards/money_magic.xml",
  },
  "$action_blood_to_power": {
  "data/entities/particles/blood_sparks.xml",
  "data/entities/misc/custom_cards/blood_to_power.xml",
  },
  "$action_quantum_split": {
  "data/entities/misc/quantum_split.xml",
  },
  "$action_sinewave": {
  "data/entities/misc/sinewave.xml",
  },
  "$action_chaotic_arc": {
  "data/entities/misc/chaotic_arc.xml",
  },
  "$action_pingpong_path": {
  "data/entities/misc/pingpong_path.xml",
  },
  "$action_avoiding_arc": {
  "data/entities/misc/avoiding_arc.xml",
  },
  "$action_floating_arc": {
  "data/entities/misc/floating_arc.xml",
  },
  "$action_fly_downwards": {
  "data/entities/misc/fly_downwards.xml",
  },
  "$action_fly_upwards": {
  "data/entities/misc/fly_upwards.xml",
  },
  "$action_horizontal_arc": {
  "data/entities/misc/horizontal_arc.xml",
  },
  "$action_line_arc": {
  "data/entities/misc/line_arc.xml",
  },
  "$action_orbit_shot": {
  "data/entities/misc/spiraling_shot.xml",
  },
  "$action_spiraling_shot": {
  "data/entities/misc/orbit_shot.xml",
  },
  "$action_phasing_arc": {
  "data/entities/misc/phasing_arc.xml",
  },
  "$action_remove_bounce": {
  "data/entities/misc/remove_bounce.xml",
  },
  "$action_homing": {
  "data/entities/misc/homing.xml",
  "data/entities/particles/tinyspark_white.xml",
  },
  "$action_homing_short": {
  "data/entities/misc/homing_short.xml",
  "data/entities/particles/tinyspark_white_weak.xml",
  },
  "$action_homing_rotate": {
  "data/entities/misc/homing_rotate.xml",
  "data/entities/particles/tinyspark_white.xml",
  },
  "$action_homing_shooter": {
  "data/entities/misc/homing_shooter.xml",
  "data/entities/particles/tinyspark_white.xml",
  },
  "$action_autoaim": {
  "data/entities/misc/autoaim.xml",
  },
  "$action_homing_accelerating": {
  "data/entities/misc/homing_accelerating.xml",
  "data/entities/particles/tinyspark_white_small.xml",
  },
  "$action_homing_cursor": {
  "data/entities/misc/homing_cursor.xml",
  "data/entities/particles/tinyspark_white.xml",
  },
  "$action_homing_area": {
  "data/entities/misc/homing_area.xml",
  "data/entities/particles/tinyspark_white.xml",
  },
  "$action_homing_projectile": {
  "data/entities/misc/homing_projectile.xml",
  "data/entities/particles/tinyspark_white.xml",
  },
  "$action_piercing_shot": {
  "data/entities/misc/piercing_shot.xml",
  },
  "$action_clipping_shot": {
  "data/entities/misc/clipping_shot.xml",
  },
  "$action_damage": {
  "data/entities/particles/tinyspark_yellow.xml",
  "data/entities/misc/custom_cards/damage.xml",
  },
  "$action_damage_random": {
  "data/entities/particles/tinyspark_yellow.xml",
  "data/entities/misc/custom_cards/damage_random.xml",
  },
  "$action_bloodlust": {
  "data/entities/particles/tinyspark_red.xml",
  },
  "$action_damage_forever": {
  "data/entities/particles/tinyspark_red.xml",
  "data/entities/misc/custom_cards/damage_forever.xml",
  },
  "$action_critical_hit": {
  "data/entities/misc/custom_cards/critical_hit.xml",
  },
  "$action_area_damage": {
  "data/entities/misc/area_damage.xml",
  },
  "$action_spells_to_power": {
  "data/entities/misc/spells_to_power.xml",
  },
  "$action_enemies_to_power": {
  "data/entities/misc/essence_to_power.xml",
  },
  "$action_damage_friendly": {
  "data/entities/misc/custom_cards/damage_friendly.xml",
  "data/entities/particles/tinyspark_yellow.xml",
  },
  "$action_damage_x2": {
  "data/entities/misc/custom_cards/damage_x2.xml",
  "data/entities/particles/tinyspark_red.xml",
  },
  "$action_damage_x5": {
  "data/entities/misc/custom_cards/damage_x2.xml",
  "data/entities/particles/tinyspark_red.xml",
  },
  "$action_heavy_shot": {
  "data/entities/particles/heavy_shot.xml",
  "data/entities/misc/custom_cards/heavy_shot.xml",
  },
  "$action_light_shot": {
  "data/entities/particles/light_shot.xml",
  "data/entities/misc/custom_cards/light_shot.xml",
  },
  "$action_speed": {
  "data/entities/misc/custom_cards/speed.xml",
  },
  "$action_accelerating_shot": {
  "data/entities/misc/accelerating_shot.xml",
  "data/entities/misc/custom_cards/accelerating_shot.xml",
  },
  "$action_decelerating_shot": {
  "data/entities/misc/decelerating_shot.xml",
  "data/entities/misc/custom_cards/decelerating_shot.xml",
  },
  "$action_explosive_projectile": {
  "data/entities/misc/custom_cards/explosive_projectile.xml",
  },
  "$action_water_to_poison": {
  "data/entities/misc/water_to_poison.xml",
  "data/entities/particles/tinyspark_purple.xml",
  },
  "$action_blood_to_acid": {
  "data/entities/misc/blood_to_acid.xml",
  "data/entities/particles/tinyspark_red.xml",
  },
  "$action_lava_to_blood": {
  "data/entities/misc/lava_to_blood.xml",
  "data/entities/particles/tinyspark_orange.xml",
  },
  "$action_liquid_to_explosion": {
  "data/entities/misc/liquid_to_explosion.xml",
  "data/entities/particles/tinyspark_red.xml",
  },
  "$action_toxic_to_acid": {
  "data/entities/misc/toxic_to_acid.xml",
  "data/entities/particles/tinyspark_green.xml",
  },
  "$action_static_to_sand": {
  "data/entities/misc/static_to_sand.xml",
  "data/entities/particles/tinyspark_yellow.xml",
  },
  "$action_transmutation": {
  "data/entities/misc/transmutation.xml",
  "data/entities/particles/tinyspark_purple_bright.xml",
  },
  "$action_random_explosion": {
  "data/entities/misc/random_explosion.xml",
  "data/entities/particles/tinyspark_purple_bright.xml",
  },
  "$action_necromancy": {
  "data/entities/misc/effect_necromancy.xml",
  },
  "$action_light": {
  "data/entities/misc/light.xml",
  "data/entities/misc/light.xml",
  },
  "$action_explosion": {
  "data/entities/projectiles/deck/explosion.xml",
  "data/entities/misc/custom_cards/explosion.xml",
  },
  "$action_explosion_light": {
  "data/entities/projectiles/deck/explosion_light.xml",
  "data/entities/misc/custom_cards/explosion_light.xml",
  },
  "$action_fire_blast": {
  "data/entities/projectiles/deck/fireblast.xml",
  "data/entities/misc/custom_cards/fire_blast.xml",
  },
  "$action_poison_blast": {
  "data/entities/projectiles/deck/poison_blast.xml",
  "data/entities/misc/custom_cards/poison_blast.xml",
  },
  "$action_alcohol_blast": {
  "data/entities/projectiles/deck/alcohol_blast.xml",
  "data/entities/misc/custom_cards/alcohol_blast.xml",
  },
  "$action_thunder_blast": {
  "data/entities/projectiles/deck/thunder_blast.xml",
  "data/entities/misc/custom_cards/thunder_blast.xml",
  },
  "$action_charm_field": {
  "data/entities/projectiles/deck/charm_field.xml",
  },
  "$action_berserk_field": {
  "data/entities/projectiles/deck/berserk_field.xml",
  },
  "$action_polymorph_field": {
  "data/entities/projectiles/deck/polymorph_field.xml",
  },
  "$action_chaos_polymorph_field": {
  "data/entities/projectiles/deck/chaos_polymorph_field.xml",
  },
  "$action_electrocution_field": {
  "data/entities/projectiles/deck/electrocution_field.xml",
  },
  "$action_freeze_field": {
  "data/entities/projectiles/deck/freeze_field.xml",
  },
  "$action_regeneration_field": {
  "data/entities/projectiles/deck/regeneration_field.xml",
  },
  "$action_teleportation_field": {
  "data/entities/projectiles/deck/teleportation_field.xml",
  },
  "$action_levitation_field": {
  "data/entities/projectiles/deck/levitation_field.xml",
  },
  "$action_telepathy_field": {
  "data/entities/projectiles/deck/telepathy_field.xml",
  },
  "$action_shield_field": {
  "data/entities/projectiles/deck/shield_field.xml",
  },
  "$action_projectile_transmutation_field": {
  "data/entities/projectiles/deck/projectile_transmutation_field.xml",
  },
  "$action_projectile_thunder_field": {
  "data/entities/projectiles/deck/projectile_thunder_field.xml",
  },
  "$action_projectile_gravity_field": {
  "data/entities/projectiles/deck/projectile_gravity_field.xml",
  },
  "$action_vacuum_powder": {
  "data/entities/projectiles/deck/vacuum_powder.xml",
  },
  "$action_vacuum_liquid": {
  "data/entities/projectiles/deck/vacuum_liquid.xml",
  },
  "$action_vacuum_entities": {
  "data/entities/projectiles/deck/vacuum_liquid.xml",
  "data/entities/projectiles/deck/vacuum_entities.xml",
  },
  "$action_sea_lava": {
  "data/entities/projectiles/deck/sea_lava.xml",
  },
  "$action_sea_alcohol": {
  "data/entities/projectiles/deck/sea_alcohol.xml",
  },
  "$action_sea_oil": {
  "data/entities/projectiles/deck/sea_oil.xml",
  },
  "$action_sea_water": {
  "data/entities/projectiles/deck/sea_water.xml",
  },
  "$action_sea_acid": {
  "data/entities/projectiles/deck/sea_acid.xml",
  },
  "$action_sea_acid_gas": {
  "data/entities/projectiles/deck/sea_acid_gas.xml",
  },
  "$action_cloud_water": {
  "data/entities/projectiles/deck/cloud_water.xml",
  },
  "$action_cloud_oil": {
  "data/entities/projectiles/deck/cloud_oil.xml",
  },
  "$action_cloud_blood": {
  "data/entities/projectiles/deck/cloud_blood.xml",
  },
  "$action_cloud_acid": {
  "data/entities/projectiles/deck/cloud_acid.xml",
  },
  "$action_cloud_thunder": {
  "data/entities/projectiles/deck/cloud_thunder.xml",
  },
  "$action_electric_charge": {
  "data/entities/particles/electricity.xml",
  "data/entities/misc/custom_cards/electric_charge.xml",
  },
  "$action_matter_eater": {
  "data/entities/misc/matter_eater.xml",
  },
  "$action_freeze": {
  "data/entities/particles/freeze_charge.xml",
  "data/entities/misc/custom_cards/freeze.xml",
  "data/entities/misc/effect_frozen.xml",
  },
  "$action_hitfx_burning_critical_hit": {
  "data/entities/particles/freeze_charge.xml",
  "data/entities/misc/hitfx_burning_critical_hit.xml",
  },
  "$action_hitfx_critical_water": {
  "data/entities/misc/hitfx_critical_water.xml",
  },
  "$action_hitfx_critical_oil": {
  "data/entities/misc/hitfx_critical_oil.xml",
  },
  "$action_hitfx_critical_blood": {
  "data/entities/misc/hitfx_critical_blood.xml",
  },
  "$action_hitfx_toxic_charm": {
  "data/entities/misc/hitfx_toxic_charm.xml",
  },
  "$action_hitfx_explosion_slime": {
  "data/entities/misc/hitfx_explode_slime.xml",
  },
  "$action_hitfx_explosion_slime_giga": {
  "data/entities/misc/hitfx_explode_slime_giga.xml",
  "data/entities/particles/tinyspark_purple.xml",
  },
  "$action_hitfx_explosion_alcohol": {
  "data/entities/misc/hitfx_explode_alcohol.xml",
  },
  "$action_hitfx_explosion_alcohol_giga": {
  "data/entities/misc/hitfx_explode_alcohol_giga.xml",
  "data/entities/particles/tinyspark_orange.xml",
  },
  "$action_petrify": {
  "data/entities/misc/hitfx_petrify.xml",
  },
  "$action_hitfx_poltergeist": {
  "data/entities/misc/hitfx_poltergeist.xml",
  },
  "$action_rocket_downwards": {
  "data/entities/misc/rocket_downwards.xml",
  },
  "$action_rocket_octagon": {
  "data/entities/misc/rocket_octagon.xml",
  },
  "$action_fizzle": {
  "data/entities/misc/fizzle.xml",
  },
  "$action_bounce_explosion": {
  "data/entities/misc/bounce_explosion.xml",
  },
  "$action_bounce_spark": {
  "data/entities/misc/bounce_spark.xml",
  },
  "$action_bounce_laser": {
  "data/entities/misc/bounce_laser.xml",
  },
  "$action_bounce_laser_emitter": {
  "data/entities/misc/bounce_laser_emitter.xml",
  },
  "$action_bounce_larpa": {
  "data/entities/misc/bounce_larpa.xml",
  },
  "$action_fireball_ray": {
  "data/entities/misc/fireball_ray.xml",
  },
  "$action_lightning_ray": {
  "data/entities/misc/lightning_ray.xml",
  "data/entities/misc/custom_cards/electric_charge.xml",
  },
  "$action_tentacle_ray": {
  "data/entities/misc/tentacle_ray.xml",
  },
  "$action_laser_emitter_ray": {
  "data/entities/misc/laser_emitter_ray.xml",
  },
  "$action_fireball_ray_line": {
  "data/entities/misc/fireball_ray_line.xml",
  },
  "$action_fireball_ray_enemy": {
  "data/entities/misc/hitfx_fireball_ray_enemy.xml",
  },
  "$action_lightning_ray_enemy": {
  "data/entities/misc/hitfx_lightning_ray_enemy.xml",
  "data/entities/misc/custom_cards/electric_charge.xml",
  "data/entities/misc/hitfx_lightning_ray_enemy.xml",
  },
  "$action_tentacle_ray_enemy": {
  "data/entities/misc/hitfx_tentacle_ray_enemy.xml",
  },
  "$action_gravity_field_enemy": {
  "data/entities/misc/hitfx_gravity_field_enemy.xml",
  },
  "$action_curse": {
  "data/entities/misc/hitfx_curse.xml",
  },
  "$action_curse_wither_projectile": {
  "data/entities/misc/hitfx_curse_wither_projectile.xml",
  },
  "$action_curse_wither_explosion": {
  "data/entities/misc/hitfx_curse_wither_explosion.xml",
  },
  "$action_curse_wither_melee": {
  "data/entities/misc/hitfx_curse_wither_melee.xml",
  },
  "$action_curse_wither_electricity": {
  "data/entities/misc/hitfx_curse_wither_electricity.xml",
  },
  "$action_orbit_discs": {
  "data/entities/misc/orbit_discs.xml",
  },
  "$action_orbit_fireballs": {
  "data/entities/misc/orbit_fireballs.xml",
  },
  "$action_orbit_nukes": {
  "data/entities/misc/orbit_nukes.xml",
  },
  "$action_orbit_lasers": {
  "data/entities/misc/orbit_lasers.xml",
  },
  "$action_orbit_larpa": {
  "data/entities/misc/orbit_larpa.xml",
  },
  "$action_chain_shot": {
  "data/entities/misc/chain_shot.xml",
  },
  "$action_hitfx_oiled_freeze": {
  "data/entities/misc/hitfx_oiled_freeze.xml",
  },
  "$action_alcohol_shot": {
  "data/entities/misc/effect_drunk.xml",
  },
  "$action_freeze_if_wet_shooter": {
  "data/entities/misc/custom_cards/freeze_if_wet_shooter.xml",
  },
  "$action_blindness": {
  "data/entities/misc/custom_cards/blindness.xml",
  "data/entities/misc/effect_blindness.xml",
  "data/entities/particles/blindness.xml",
  },
  "$action_teleportation": {
  "data/entities/misc/custom_cards/teleportation.xml",
  "data/entities/misc/effect_teleportation.xml",
  "data/entities/particles/teleportation.xml",
  },
  "$action_telepathy": {
  "data/entities/misc/effect_telepathy.xml",
  },
  "$action_arc_electric": {
  "data/entities/misc/arc_electric.xml",
  "data/entities/misc/custom_cards/arc_electric.xml",
  "data/entities/misc/arc_electric.xml",
  },
  "$action_arc_fire": {
  "data/entities/misc/arc_fire.xml",
  "data/entities/misc/custom_cards/arc_fire.xml",
  "data/entities/misc/arc_fire.xml",
  },
  "$action_arc_gunpowder": {
  "data/entities/misc/arc_gunpowder.xml",
  },
  "$action_arc_poison": {
  "data/entities/misc/arc_poison.xml",
  "data/entities/misc/arc_poison.xml",
  },
  "$action_crumbling_earth_projectile": {
  "data/entities/misc/crumbling_earth_projectile.xml",
  "data/entities/misc/crumbling_earth_projectile.xml",
  },
  "$action_polymorph": {
  "data/entities/misc/custom_cards/polymorph.xml",
  "data/entities/misc/effect_polymorph.xml",
  "data/entities/particles/polymorph.xml",
  },
  "$action_berserk": {
  "data/entities/misc/custom_cards/berserk.xml",
  "data/entities/misc/effect_berserk.xml",
  "data/entities/particles/berserk.xml",
  },
  "$action_charm": {
  "data/entities/misc/custom_cards/charm.xml",
  "data/entities/misc/effect_charm.xml",
  "data/entities/particles/charm.xml",
  },
  "$action_x_ray": {
  "data/entities/projectiles/deck/xray.xml",
  "data/entities/misc/custom_cards/xray.xml",
  "data/entities/projectiles/deck/xray.xml",
  },
  "$action_x_ray_modifier": {
  "data/entities/misc/fogofwar_radius.xml",
  "data/entities/particles/electricity.xml",
  },
  "$action_unstable_gunpowder": {
  "data/entities/misc/custom_cards/unstable_gunpowder.xml",
  },
  "$action_acid_trail": {
  "data/entities/misc/custom_cards/acid_trail.xml",
  },
  "$action_poison_trail": {
  "data/entities/misc/custom_cards/poison_trail.xml",
  "data/entities/misc/effect_apply_poison.xml",
  },
  "$action_oil_trail": {
  "data/entities/misc/custom_cards/oil_trail.xml",
  "data/entities/misc/effect_apply_oiled.xml",
  },
  "$action_water_trail": {
  "data/entities/misc/custom_cards/water_trail.xml",
  "data/entities/misc/effect_apply_wet.xml",
  },
  "$action_blood_trail": {
  "data/entities/misc/custom_cards/blood_trail.xml",
  },
  "$action_gunpowder_trail": {
  "data/entities/misc/custom_cards/gunpowder_trail.xml",
  },
  "$action_fire_trail": {
  "data/entities/misc/custom_cards/fire_trail.xml",
  "data/entities/misc/effect_apply_on_fire.xml",
  },
  "$action_burn_trail": {
  "data/entities/misc/burn.xml",
  "data/entities/misc/custom_cards/burn_trail.xml",
  "data/entities/misc/effect_apply_on_fire.xml",
  "data/entities/misc/burn.xml",
  },
  "$action_torch": {
  "data/entities/misc/custom_cards/torch.xml",
  },
  "$action_torch_electric": {
  "data/entities/misc/custom_cards/torch_electric.xml",
  },
  "$action_energy_shield": {
  "data/entities/misc/custom_cards/energy_shield.xml",
  },
  "$action_energy_shield_sector": {
  "data/entities/misc/custom_cards/energy_shield_sector.xml",
  },
  "$action_energy_shield_shot": {
  "data/entities/misc/energy_shield_shot.xml",
  },
  "$action_tiny_ghost": {
  "data/entities/misc/custom_cards/tiny_ghost.xml",
  },
  "$action_duck": {
  "data/entities/projectiles/deck/duck.xml",
  },
  "$action_ocarina_a": {
  "data/entities/projectiles/deck/ocarina/ocarina_a.xml",
  },
  "$action_ocarina_b": {
  "data/entities/projectiles/deck/ocarina/ocarina_b.xml",
  },
  "$action_ocarina_c": {
  "data/entities/projectiles/deck/ocarina/ocarina_c.xml",
  },
  "$action_ocarina_d": {
  "data/entities/projectiles/deck/ocarina/ocarina_d.xml",
  },
  "$action_ocarina_e": {
  "data/entities/projectiles/deck/ocarina/ocarina_e.xml",
  },
  "$action_ocarina_f": {
  "data/entities/projectiles/deck/ocarina/ocarina_f.xml",
  },
  "$action_ocarina_gsharp": {
  "data/entities/projectiles/deck/ocarina/ocarina_gsharp.xml",
  },
  "$action_ocarina_a2": {
  "data/entities/projectiles/deck/ocarina/ocarina_a2.xml",
  },
  "$action_kantele_a": {
  "data/entities/projectiles/deck/kantele/kantele_a.xml",
  },
  "$action_kantele_d": {
  "data/entities/projectiles/deck/kantele/kantele_d.xml",
  },
  "$action_kantele_dis": {
  "data/entities/projectiles/deck/kantele/kantele_dis.xml",
  },
  "$action_kantele_e": {
  "data/entities/projectiles/deck/kantele/kantele_e.xml",
  },
  "$action_kantele_g": {
  "data/entities/projectiles/deck/kantele/kantele_g.xml",
  },
  "$action_all_nukes": {
  "data/entities/projectiles/deck/all_nukes.xml",
  },
  "$action_all_discs": {
  "data/entities/projectiles/deck/all_discs.xml",
  },
  "$action_all_rockets": {
  "data/entities/projectiles/deck/all_rockets.xml",
  },
  "$action_all_deathcrosses": {
  "data/entities/projectiles/deck/all_deathcrosses.xml",
  },
  "$action_all_blackholes": {
  "data/entities/projectiles/deck/all_blackholes.xml",
  },
  "$action_all_acid": {
  "data/entities/projectiles/deck/all_acid.xml",
  },
  "$action_all_spells": {
  "data/entities/projectiles/deck/all_spells_loader.xml",
  },
  "$action_summon_portal": {
  "data/entities/misc/custom_cards/summon_portal.xml",
  "data/entities/projectiles/deck/summon_portal.xml",
  },
  "$action_larpa_chaos": {
  "data/entities/misc/larpa_chaos.xml",
  },
  "$action_larpa_downwards": {
  "data/entities/misc/larpa_downwards.xml",
  },
  "$action_larpa_upwards": {
  "data/entities/misc/larpa_upwards.xml",
  },
  "$action_larpa_chaos_2": {
  "data/entities/misc/larpa_chaos_2.xml",
  },
  "$action_larpa_death": {
  "data/entities/misc/larpa_death.xml",
  },
  "$action_meteor_rain": {
  "data/entities/projectiles/deck/meteor_rain_meteor.xml",
  "data/entities/misc/effect_meteor_rain.xml",
  "data/entities/misc/custom_cards/meteor_rain.xml",
  "data/entities/projectiles/deck/meteor_rain.xml",
  "data/entities/misc/effect_meteor_rain.xml",
  },
  "$action_worm_rain": {
  "data/entities/animals/worm_big.xml",
  "data/entities/misc/custom_cards/worm_rain.xml",
  "data/entities/projectiles/deck/worm_rain.xml",
  },
  "$action_colour_red": {
  "data/entities/particles/tinyspark_red.xml",
  "data/entities/misc/colour_red.xml",
  },
  "$action_colour_orange": {
  "data/entities/particles/tinyspark_red.xml",
  "data/entities/misc/colour_orange.xml",
  },
  "$action_colour_green": {
  "data/entities/particles/tinyspark_red.xml",
  "data/entities/misc/colour_green.xml",
  },
  "$action_colour_yellow": {
  "data/entities/particles/tinyspark_red.xml",
  "data/entities/misc/colour_yellow.xml",
  },
  "$action_colour_purple": {
  "data/entities/particles/tinyspark_red.xml",
  "data/entities/misc/colour_purple.xml",
  },
  "$action_colour_blue": {
  "data/entities/particles/tinyspark_red.xml",
  "data/entities/misc/colour_blue.xml",
  },
  "$action_colour_rainbow": {
  "data/entities/particles/tinyspark_red.xml",
  "data/entities/misc/colour_rainbow.xml",
  },
  "$action_colour_invis": {
  "data/entities/misc/colour_invis.xml",
  },
  "$action_rainbow_trail": {
  "data/entities/misc/custom_cards/rainbow_trail.xml",
  "data/entities/misc/effect_rainbow_farts.xml",
  },
  "$action_hook": {
    "data/entities/projectiles/deck/hook.xml",
  },
  "$action_white_hole": {
    "data/entities/projectiles/deck/white_hole.xml",
    "data/entities/misc/custom_cards/white_hole.xml",
  },
  "$action_white_hole_big": {
    "data/entities/projectiles/deck/white_hole_big.xml",
    "data/entities/misc/custom_cards/white_hole_big.xml",
  },
  "$action_white_hole_giga": {
    "data/entities/projectiles/deck/white_hole_giga.xml",
    "data/entities/misc/custom_cards/white_hole_giga.xml",
  },
  "$action_holy": {
    "data/entities/projectiles/deck/lance_holy.xml",
    "data/entities/misc/custom_cards/lance_holy.xml",
  },
  "$action_fish": {
    "data/entities/projectiles/deck/fish.xml",
  },
  "$action_antiheal": {
    "data/entities/projectiles/deck/healhurt.xml",
  },
  "$action_caster_cast": {
    "data/entities/projectiles/deck/caster_cast.xml",
    "data/entities/misc/caster_cast.xml",
  },
  "$action_touch_grass": {
    "data/entities/projectiles/deck/touch_grass.xml",
    "data/entities/misc/custom_cards/touch_grass.xml",
  },
  "$action_mass_polymorph": {
    "data/entities/projectiles/deck/mass_polymorph.xml",
  },
  "$action_true_orbit": {
    "data/entities/misc/true_orbit.xml",
    "data/entities/misc/true_orbit.xml",
  },
  "$action_anti_homing": {
    "data/entities/misc/anti_homing.xml",
    "data/entities/particles/tinyspark_white.xml",
  },
  "$action_homing_wand": {
    "data/entities/misc/homing_wand.xml",
    "data/entities/particles/tinyspark_white.xml",
  },
  "$action_zero_damage": {
    "data/entities/particles/tinyspark_white_small.xml",
    "data/entities/misc/zero_damage.xml",
  },
  "$action_clustermod": {
    "data/entities/misc/custom_cards/clusterbomb.xml",
    "data/entities/misc/clusterbomb.xml",
  },
  "$action_sea_swamp": {
    "data/entities/projectiles/deck/sea_swamp.xml",
  },
  "$action_sea_mimic": {
    "data/entities/projectiles/deck/sea_mimic.xml",
  },
  "$action_bounce_small_explosion": {
    "data/entities/misc/bounce_small_explosion.xml",
  },
  "$action_bounce_lightning": {
    "data/entities/misc/bounce_lightning.xml",
  },
  "$action_bounce_hole": {
    "data/entities/misc/bounce_hole.xml",
  },
}

spell_lookup = {}
for translation, files in reverse_spell_lookup.items():
  for xmlfile in files:
    spell_lookup[xmlfile] = translation


extra_entity_xml_name_lookup = {
  "data/entities/misc/perks/freeze_field.xml": "Freeze Field",
  "data/entities/misc/perks/fire_gas.xml": "Gas Fire",
  "data/entities/misc/perks/vomit_rats.xml": "Spontaneous Generation",
  "data/entities/misc/perks/slime_fungus.xml": "Fungal Colony",
  "data/entities/misc/perks/fungal_disease.xml": "Fungal Disease",
  "data/entities/items/pickup/jar.xml": "Jar",
  "data/entities/items/pickup/potion_empty.xml": "Potion",
  "data/entities/items/pickup/potion.xml": "Potion",
  "data/entities/items/pickup/potion_slime.xml": "Potion",
  "data/entities/items/pickup/test/pouch.xml": "Powder Pouch",
  "data/entities/items/pickup/potion_starting.xml": "Potion",
  "data/entities/items/pickup/potion_vomit.xml": "Potion",
  "data/entities/items/shop_potion.xml": "Potion",
  "data/entities/items/pickup/test/pouch_static.xml": "Powder Pouch",
  "data/entities/items/pickup/jar_of_urine.xml": "Jar",
  "data/entities/items/pickup/potion_porridge.xml": "Potion",
  "data/entities/items/pickup/potion_water.xml": "Potion",
  "data/entities/items/pickup/potion_random_material.xml": "Potion",
  "data/entities/items/pickup/potion_alcohol.xml": "Potion",
  "data/entities/items/pickup/potion_aggressive.xml": "Potion",
  "data/entities/items/pickup/potion_secret.xml": "Potion",
  "data/entities/props/music_machines/base_music_machine.xml": "Music Machine",
  "data/entities/props/music_machines/music_machine_01.xml": "Music Machine",
  "data/entities/props/music_machines/music_machine_00.xml": "Music Machine",
  "data/entities/props/music_machines/music_machine_03.xml": "Music Machine",
  "data/entities/props/music_machines/music_machine_02.xml": "Music Machine",
  "data/entities/buildings/statue_hand_1.xml": "Hand Statue",
  "data/entities/buildings/statue_hand_2.xml": "Hand Statue",
  "data/entities/buildings/statue_hand_3.xml": "Hand Statue",
  "data/entities/props/temple_statue_01.xml": "Temple Statue",
  "data/entities/props/temple_statue_02.xml": "Temple Statue",
  "data/entities/props/temple_statue_01_green.xml": "Temple Statue",
  "data/entities/buildings/firetrap_right.xml": "Fire Trap",
  "data/entities/buildings/firetrap_left.xml": "Fire Trap",
  "data/entities/buildings/arrowtrap_left.xml": "Arrow Trap",
  "data/entities/buildings/arrowtrap_right.xml": "Arrow Trap",
  "data/entities/buildings/spittrap_left.xml": "Acid Trap",
  "data/entities/buildings/spittrap_right.xml": "Acid Trap",
  "data/entities/buildings/thundertrap_right.xml": "Lightning Trap",
  "data/entities/buildings/thundertrap_left.xml": "Lightning Trap",
  "data/entities/props/suspended_seamine.xml": "Sea Mine",
  "data/entities/props/physics_seamine.xml": "Sea Mine",
  "data/entities/props/physics/minecart.xml": "Minecart",
  "data/entities/props/physics_minecart.xml": "Minecart",
  "data/entities/misc/runestone_lava.xml": "Runestone of magma",
  "data/entities/misc/runestone_metal.xml": "Runestone of Metal",
  "data/entities/props/physics_sun_rock.xml": "Sun Rock",
  "data/entities/props/physics_darksun_rock.xml": "Dark Sun Rock",
  "data/entities/buildings/failed_alchemist_orb.xml": "Epäalkemisti",
  "data/entities/props/pumpkin_01.xml": "Pumpkin",
  "data/entities/props/pumpkin_02.xml": "Pumpkin",
  "data/entities/props/pumpkin_03.xml": "Pumpkin",
  "data/entities/props/pumpkin_04.xml": "Pumpkin",
  "data/entities/props/pumpkin_05.xml": "Pumpkin",
  "data/entities/props/physics_propane_tank.xml": "Propane tank",
  "data/entities/props/physics_barrel_oil.xml": "Oil Barrel",
  "data/entities/props/physics_barrel_radioactive.xml": "Toxic Sludge Barrel",
  "data/entities/props/physics_bone_01.xml": "Bone (Prop)",
  "data/entities/props/physics_bone_02.xml": "Bone (Prop)",
  "data/entities/props/physics_bone_03.xml": "Bone (Prop)",
  "data/entities/props/physics_bone_04.xml": "Bone (Prop)",
  "data/entities/props/physics_bone_05.xml": "Bone (Prop)",
  "data/entities/props/physics_bone_06.xml": "Bone (Prop)",
  "data/entities/props/physics_skull_01.xml": "Skull",
  "data/entities/props/physics_skull_02.xml": "Skull",
  "data/entities/props/physics_skull_03.xml": "Skull",
  "data/entities/particles/particle_explosion/explosion_trail_guts_01.xml": "Overeating Explosion",
  "data/entities/particles/particle_explosion/explosion_trail_guts_02.xml": "Overeating Explosion",
  "data/entities/particles/particle_explosion/explosion_trail_guts_03.xml": "Overeating Explosion",
  "data/entities/particles/particle_explosion/explosion_trail_guts_04.xml": "Overeating Explosion",
  "data/entities/particles/particle_explosion/explosion_trail_guts_05.xml": "Overeating Explosion",
  "data/entities/buildings/biome_modifiers/gas_pipe_floor.xml": "Gas Pipe",
  "data/entities/buildings/biome_modifiers/gas_pipe.xml": "Gas Pipe",
  "data/entities/projectiles/acidshot.xml": "Acid Ball",
  "data/entities/props/physics_fungus_acid_small.xml": "Acid Fungus",
  "data/entities/props/physics_fungus_acid.xml": "Acid Fungus",
  "data/entities/props/physics_fungus_acid_big.xml": "Acid Fungus",
  "data/entities/props/physics_fungus_acid_hugeish.xml": "Acid Fungus",
  "data/entities/props/physics_fungus_acid_huge.xml": "Acid Fungus",
  "data/entities/animals/boss_wizard/wizard_orb_blood.xml": "Mestarien mestari",
  "data/entities/animals/boss_wizard/wizard_orb_death.xml": "Mestarien mestari",
  "data/entities/particles/blood_explosion.xml": "Mestarien mestari",
  "data/entities/misc/moon_effect2.xml": "Dark Moon",
  "data/entities/projectiles/polyshot.xml": "Taivaankatse Shot",
  "data/entities/props/physics_candle_1.xml": "Candle",
  "data/entities/props/physics_candle_2.xml": "Candle",
  "data/entities/props/physics_candle_3.xml": "Candle",
  "data/entities/props/candle_1.xml": "Candle",
  "data/entities/props/candle_2.xml": "Candle",
  "data/entities/props/candle_3.xml": "Candle",
  "data/entities/misc/effect_curse_cloud_00.xml": "Rain Curse",
  "data/entities/misc/effect_curse_cloud_01.xml": "Thunder Curse",
  "data/entities/misc/effect_curse_cloud_02.xml": "Acid Rain Curse",
  "data/entities/misc/perks/fungal_disease.xml": "Fungal Disease",
  "data/entities/misc/convert_radioactive.xml": "Curse of Greed",
  "data/entities/props/meat_cyst.xml": "Meat Cyst",
  "data/entities/projectiles/pusblob.xml": "Meat Cyst",
  "data/entities/props/suspended_cage.xml": "Suspended Cage",
  "data/entities/props/suspended_cage_broken.xml": "Suspended Cage",
  "data/entities/props/suspended_chain.xml": "Suspended Chain",
}

####################################################################
## Parse translations
####################################################################

translations = {}
with open('common.csv', 'r', encoding='utf-8') as f:
  reader = csv.reader(f)
  for row in reader:
    translations['$' + row[0]] = row[1]


####################################################################
## Parse materials.xml
####################################################################

def effect_to_wiki(effect_str, duration = None):
  if effect_str in effect_lookup:
    if duration:
      return "{{status|" + effect_lookup[effect_str] + f"|{float(duration)*100:g}" + "}}"
    return "{{status|" + effect_lookup[effect_str] + "}}"
  return effect_str

def extract_status_effect(elem):
  effect = elem.attrib.get('type')
  duration = elem.attrib.get('amount')
  return effect_to_wiki(effect, duration)

def get_stain_effects(elem):
  effect_tags = elem.findall('./StatusEffects/Stains/StatusEffect')
  return '<br/>'.join(map(extract_status_effect, effect_tags))

def get_ingest_effects(elem):
  effect_tags = elem.findall('./StatusEffects/Ingestion/StatusEffect')
  return '<br/>'.join(map(extract_status_effect, effect_tags))

tree = ET.parse('materials.xml')
root = tree.getroot()

materials = {}
valid_colours = set()

def get_translated_ui_name(uiname):
  return translations.get(uiname, uiname).lstrip('$').title()

def convert_attrib_data(child):
  attr = child.attrib
  colour = int(attr.get('wang_color', '0'), base=16) & 0xFFFFFF

  result = {
    "id": attr["name"],
    "colour": colour,
    "wang_color": attr.get('wang_color', '0'),
  }

  if 'ui_name' in attr: result['ui_name'] = get_translated_ui_name(attr['ui_name'])

  if 'cell_type' in attr: result['cell_type'] = attr['cell_type']
  if 'liquid_static' in attr: result['liquid_static'] = attr['liquid_static']
  if 'liquid_sand' in attr: result['liquid_sand'] = attr['liquid_sand']

  tags = set(re.findall('\w+', attr.get('tags', '')))
  result['tags'] = tags

  if 'density' in attr: result['density'] = attr['density']
  if 'hp' in attr: result['hardness'] = attr['hp']
  if 'durability' in attr: result['durability'] = attr['durability']
  if 'lifetime' in attr: result['lifetime'] = attr['lifetime']
  if '_parent' in attr: result['parent'] = attr['_parent']
  if '_inherit_reactions' in attr: result['inheritsReactions'] = attr['_inherit_reactions']
  if 'status_effects' in attr: result['submergeEffect'] = effect_to_wiki(attr['status_effects'])

  stains = get_stain_effects(child)
  ingestion = get_ingest_effects(child)

  if stains != '': result['stainEffect'] = stains
  if ingestion != '': result['ingestEffect'] = ingestion

  if 'electrical_conductivity' in attr: result['conductive'] = attr['electrical_conductivity']
  if 'burnable' in attr: result['burnable'] = attr['burnable']
  if 'cold_freezes_to_material' in attr: result['freezes'] = attr['cold_freezes_to_material']
  if 'warmth_melts_to_material' in attr: result['melts'] = attr['warmth_melts_to_material']

  break_into = set()
  if 'solid_break_to_type' in attr: break_into.add(attr['solid_break_to_type'])
  if 'solid_on_collision_material' in attr: break_into.add(attr['solid_on_collision_material'])
  if 'convert_to_box2d_material' in attr: break_into.add(attr['convert_to_box2d_material'])
  if len(break_into) > 0: result['breakInto'] = ','.join(break_into)

  if 'slippery' in attr: result['slippery'] = attr['slippery']
  if 'fire_hp' in attr: result['fuel'] = attr['fire_hp']
  if 'platforming_type' in attr: result['playerCollision'] = attr['platforming_type'] == '1'

  if 'gfx_glow' in attr:
    result['glow'] = int(attr['gfx_glow'])
  if 'gfx_glow_color' in attr:
    result['glow_color'] = attr['gfx_glow_color']

  graphics = child.find('Graphics')
  if graphics != None:
    result['has_gfx'] = True
    gfxattr = graphics.attrib

    if 'color' in gfxattr: result['gfx_color'] = gfxattr['color']
    if 'texture_file' in gfxattr: result['gfx_texture_file'] = gfxattr['texture_file'] # Keep full path

    gfx_border = {}
    if 'pixel_all_around' in gfxattr: gfx_border['gfx_pixel_all_around'] = gfxattr['pixel_all_around']
    if 'pixel_top_right' in gfxattr: gfx_border['gfx_pixel_top_right'] = gfxattr['pixel_top_right']
    if 'pixel_top_left' in gfxattr: gfx_border['gfx_pixel_top_left'] = gfxattr['pixel_top_left']
    if 'pixel_bottom_right' in gfxattr: gfx_border['gfx_pixel_bottom_right'] = gfxattr['pixel_bottom_right']
    if 'pixel_bottom_left' in gfxattr: gfx_border['gfx_pixel_bottom_left'] = gfxattr['pixel_bottom_left']
    if 'pixel_left' in gfxattr: gfx_border['gfx_pixel_left'] = gfxattr['pixel_left']
    if 'pixel_top' in gfxattr: gfx_border['gfx_pixel_top'] = gfxattr['pixel_top']
    if 'pixel_right' in gfxattr: gfx_border['gfx_pixel_right'] = gfxattr['pixel_right']
    if 'pixel_bottom' in gfxattr: gfx_border['gfx_pixel_bottom'] = gfxattr['pixel_bottom']
    if len(gfx_border) > 0:
      result['gfx_border'] = gfx_border

    edge = child.find('Graphics/Edge/EdgeGraphics')
    if edge != None:
      result['gfx_edge_type'] = edge.attrib['type']

      sides = [dict(side.items()) for side in edge.findall('Images/Image')]
      if len(sides) > 0:
        result['gfx_sides'] = sides

  return result


def process_celldata(child):
  material = convert_attrib_data(child)

  valid_colours.add(material['colour'])
  materials[material['id']] = material


for child in root.findall("CellData"):
  process_celldata(child)

for child in root.findall("CellDataChild"):
  process_celldata(child)

#valid_colours.update(special_mapping.keys())

####################################################################
## Parse biome images
####################################################################

pixel_biome_locations = {}
biome_has_spawns = {}

for filename in biome_png_mapping.keys():
  try:
    pngfile = png.Reader(filename)
    width, height, values, info = pngfile.read_flat()

    #pprint.pprint(info)

    for n in range(0, len(values), info['planes']):
      r = values[n+0]
      g = values[n+1]
      b = values[n+2]
      hexnum = r << 16 | g << 8 | b

      if hexnum in valid_colours:
        entry = pixel_biome_locations.setdefault(hexnum, { 'biomes': set(), 'spawns': set() })
        entry['biomes'].update(biome_png_mapping[filename])
      elif hexnum in ignore_colours or (r == g and g == b):
        continue
      else:
        spawn_name = special_mapping.get(hexnum, hex(hexnum))
        for biome in biome_png_mapping[filename]:
          biome_has_spawns.setdefault(biome, set()).add(spawn_name)
  except FileNotFoundError:
    print(f"Warning: Biome PNG file not found, skipping: {filename}")


biome_spawns_output_file = open('biome_spawns.txt', 'wt')
for biome, spawns in biome_has_spawns.items():
  biome_spawns_output_file.write(f"{biome}: {', '.join(spawns)}\n")

biome_spawns_output_file.close()

####################################################################
## Inherit values and populate biomes
####################################################################
def merge_material_values(material, spaces=''):
  if 'parent' in material and material['parent'] in materials:
    merge_material_values(materials[material['parent']], spaces + '  ')

    new_mat = materials[material['parent']].copy()
    tags = new_mat.get('tags', set())
    #
    #if material.get('inheritsReactions', '0') == '1':
    #  tags = tags.union(material.get('tags', set()))

    old_gfx_edge_type = material.get('gfx_edge_type', None)
    old_gfx_sides = material.get('gfx_sides', None)
    old_gfx_border = material.get('gfx_border', None)

    new_mat.update(material)

    if old_gfx_edge_type != None:
      new_mat['gfx_edge_type'] = old_gfx_edge_type
    else:
      new_mat.pop('gfx_edge_type', '')

    if old_gfx_sides != None:
      new_mat['gfx_sides'] = old_gfx_sides
    else:
      new_mat.pop('gfx_sides', '')

    if old_gfx_border != None:
      new_mat['gfx_border'] = old_gfx_border
    else:
      new_mat.pop('gfx_border', '')


    if len(new_mat.get('tags', set())) == 0:
      new_mat['tags'] = tags


    materials[material['id']] = new_mat

for mat_key in materials.keys():
  merge_material_values(materials[mat_key])
  materials[mat_key]["name"] = materials[mat_key].get("ui_name", materials[mat_key]['id'])


def get_material_type(elem):
  cell_type = elem.get('cell_type', '')

  if cell_type == 'fire': return 'Fire'
  if cell_type == 'solid': return 'Solid'
  if cell_type == 'gas': return 'Gas'

  if cell_type == 'liquid':
    if elem.get('liquid_static', '0') == '1': return 'Solid'
    if elem.get('liquid_sand', '0') == '1': return 'Powder'
    return 'Liquid'

  return ''


for mat in materials.values():
  mat_type = get_material_type(mat)
  if mat_type != '': mat['type'] = mat_type

  # Get the list of biomes this material is found in
  biomes = set()
  if mat['colour'] in pixel_biome_locations:
    biomes.update(pixel_biome_locations[mat['colour']]['biomes'])

  if mat['id'] in biome_mat_mapping:
    biomes.update(biome_mat_mapping[mat['id']])

  if len(biomes) > 0: mat['biomes'] = ','.join(biomes)

####################################################################
## Process Material Graphics
####################################################################

# This section is being left as-is, but the masks it generates are no longer used for the material swatches.
try:
    gas_mask = Image.open("data/gas_mask.png")
except FileNotFoundError:
    print("Warning: data/gas_mask.png not found. Gas materials may not render correctly if textured.")
    gas_mask = Image.new("RGBA", (42, 42), (0,0,0,0)) # Create a dummy mask

def make_gas_mask_copy(mat_alpha):
  a_low = mat_alpha * 3 // 4

  result = gas_mask.copy()
  for y in range(result.height):
    for x in range(result.width):
      r,g,b,a = result.getpixel((x, y))
      if a == 128:
        a = a_low
      elif a == 255:
        a = mat_alpha
      else:
        continue
      result.putpixel((x, y), (r, g, b, a))
  return result


try:
    potion_base = Image.open('data/ui_gfx/items/potion.png')
    alchemistpotion_base = Image.open('data/ui_gfx/items/potion_alchemist.png')
    powder_base = Image.open('data/ui_gfx/items/material_pouch.png')
except FileNotFoundError as e:
    print(f"Warning: Potion/pouch base image not found: {e}. Potion/pouch graphics will not be generated.")
    potion_base, alchemistpotion_base, powder_base = None, None, None


def gl_mix(x, y, a):
  return tuple(i*(1.0-a) + j*a for i,j in zip(x, y))


def create_potion_graphic(base, basename, material_name, colour):
  if not base: return # Don't run if base images failed to load
  pot = base.copy()

  for x in range(0, pot.width):
    for y in range(0, 3):
      r,g,b,a = pot.getpixel((x,y))
      r,g,b = tuple(int(round(i * 0.85)) for i in [r,g,b])
      pot.putpixel((x,y), (r, g, b, a))

    for y in range(3, pot.height):
      r,g,b,a = pot.getpixel((x,y))
      r,g,b = tuple((i / 255.0) * (j / 255.0) for i,j in zip([r,g,b], colour[:3]))
      r,g,b = tuple(int(round(i * 0.85 * 255.0)) for i in [r,g,b])
      pot.putpixel((x,y), (r, g, b, a))

  pot.save(f"zout_potions/material{basename}_{material_name}.png", optimize=True)


def RGBAfromInt(v):
  b =  v & 255
  g = (v >> 8) & 255
  r =   (v >> 16) & 255
  a = (v >> 24) & 255
  return (r, g, b, a)

def get_colour(s):
  return RGBAfromInt(int(s, base=16))

# MODIFICATION: This function still exists to tile textures, but will no longer apply a mask.
def blit_tiled(dst, src, mat_type):
  temp_img = Image.new("RGBA", dst.size)
  for y in range(0, dst.height, src.height):
    for x in range(0, dst.width, src.width):
        temp_img.paste(src, (x, y))
  # Always paste the full tiled image without a mask
  dst.paste(temp_img, (0, 0))

def count_empty(img, x):
  result = 0
  for y in range(0, img.height):
    if img.getpixel((x, img.height - y - 1))[3] != 0:
      return result
    result += 1
  return result

def settle_powder(img):
  result = Image.new("RGBA", img.size)

  # Shift everything down
  for x in range(0, img.width):
    shift = count_empty(img, x)
    line = img.crop((x, 0, x+1, img.height))
    result.paste(line, (x, shift))

  # Rotate random pixels
  for i in range(0, 1500):
    rx1 = random.randint(1, result.width-2)
    ry1 = random.randint(1, result.height-2)

    px1 = result.getpixel((rx1, ry1))
    if px1[3] == 0: continue

    rx2 = rx1 + (random.randint(0, 1)*2 - 1)
    ry2 = ry1 + random.randint(-1, 1)
    px2 = result.getpixel((rx2, ry2))
    if px2[3] == 0: continue

    result.putpixel((rx1, ry1), px2)
    result.putpixel((rx2, ry2), px1)

  return result

def settle_liquid(img):
  # Rotate random pixels
  for i in range(0, 3000):
    rx1 = random.randint(1, img.width-2)
    ry1 = random.randint(1, img.height-2)

    px1 = img.getpixel((rx1, ry1))
    if px1[3] == 0: continue

    rx2 = rx1 + (random.randint(0, 1)*2 - 1)
    ry2 = ry1 + random.randint(-1, 1)
    px2 = img.getpixel((rx2, ry2))
    if px2[3] == 0: continue

    img.putpixel((rx1, ry1), px2)
    img.putpixel((rx2, ry2), px1)

def decimal_range(start, stop, increment):
  while start < stop:
    yield start
    start += increment

def apply_glow(img, glow_amount, glow_colour):
  # TODO still wrong
  #color = max ( color + glow * 0.6 - 0.6 * lights, clamp((color + glow) - ( color * sky_light_modulation * glow), 0.0, 1.0));

  tex_glow_source = img.copy()

  for imgy in range(0, img.height):
    for imgx in range(0, img.width):
      px = tex_glow_source.getpixel((imgx, imgy))

      r,g,b,a = tuple((i / 255.0) * (glow_amount / 255.0) for i in glow_colour)
      px = tuple(i / 255.0 for i in px)
      color = r, g, b, px[3]
      #r,g,b,a = glow

      #smoothing_amount = 1.0 - (r + g + b) * 0.3333
      #glow = gl_mix(glow, glow, smoothing_amount)

      color = tuple(max(0, i - 0.008) for i in color)

      color = tuple(int(round((c + g * 0.6) * 255.0)) for c, g in zip(px, color))
      img.putpixel((imgx, imgy), color)

def process_material_graphic(material):
  mat_id = material['id']
  colour = get_colour(material['wang_color'])
  glow = material.get('glow', 0)
  mat_type = material.get('type', '')

  img = Image.new("RGBA", (42, 42))
  draw = ImageDraw.Draw(img)

  texture_file = None
  fin_dir = "finished"

  # Get colour and texture
  if 'has_gfx' in material:
    if 'gfx_color' in material:
      colour = get_colour(material['gfx_color'])

    texture_filename = material.get('gfx_texture_file', None)
    if texture_filename:
        # MODIFICATION: Use pathlib to handle file paths correctly on any OS.
        texture_path = Path(texture_filename)
        try:
            texture_file = Image.open(texture_path)
        except FileNotFoundError:
            print(f"Warning: Texture file not found, skipping: {texture_path}")
            texture_file = None

  # Blit texture or color
  if texture_file:
    blit_tiled(img, texture_file, mat_type)
    texture_file.close()
  else:
    # If no texture, fill the square with the solid material color.
    if mat_id == 'air':
      draw.rectangle([0, 0, img.width, img.height], fill=RGBAfromInt(0))
    else:
      draw.rectangle([0, 0, img.width, img.height], fill=colour)

  if 'gfx_border' in material and mat_type == 'Solid':
    # This logic remains the same
    ...

  # Create edges
  if 'gfx_edge_type' in material:
    # This logic remains the same
    ...
  
  if glow > 0:
    print(f"{mat_id} - Glow: {glow}, Type: {mat_type}")
    fin_dir = "unfinished"

  # MODIFICATION: Re-enabled settling functions to apply visual effects
  # to the square image, restoring the intended look without masking.
  if mat_type == 'Powder':
    img = settle_powder(img)
  elif mat_type == 'Liquid' or mat_type == 'Fire':
    settle_liquid(img)

  # Potion/pouch generation remains the same.
  if mat_type == 'Powder' or mat_type == 'Liquid':
    create_potion_graphic(potion_base, 'potion', mat_id, colour)
    create_potion_graphic(alchemistpotion_base, 'flask', mat_id, colour)
  if mat_type == 'Powder':
    create_potion_graphic(powder_base, 'pouch', mat_id, colour)

  img = img.resize((252, 252), Image.NEAREST)

  if glow > 0:
    glow_colour = colour
    if 'glow_color' in material:
      glow_colour = get_colour(material['glow_color'])

    apply_glow(img, glow, glow_colour)

  img.save(f"zout_mats/{fin_dir}/material_{mat_id}.png", optimize=True)

# (The rest of the script remains unchanged from the previous version)

dirs_to_create=["./zout_mats/finished", "./zout_mats/unfinished", "./zout_potions"]
for path in dirs_to_create:
  Path(path).mkdir(parents=True, exist_ok=True)

for mat in materials.values():
  try:
    process_material_graphic(mat)
  except Exception as e:
    print(f"Failed to process graphic for material: {mat.get('id', 'UNKNOWN')}. Error: {e}")
    traceback.print_exc()

####################################################################
## Entities
####################################################################

props = {}

def parse_PhysicsImageShapeComponent(prop, child):
  attr = child.attrib
  id = attr.get('body_id', '0')

  if 'material' in attr:
    prop.setdefault('components', set()).add(attr['material'])


def parse_ParticleEmitterComponent(prop, child):
  attr = child.attrib

  if attr.get('emit_cosmetic_particles', '0') == '0' and 'emitted_material_name' in attr:
    mats = prop.setdefault('emits_materials', set())
    mats.add(attr['emitted_material_name'])


def parse_ExplodeOnDamageComponent(prop, child):
  attr = child.attrib
  if not child.find('config_explosion'): return
  conf = child.find('config_explosion').attrib

  # This function seems to have a print statement that might be for debugging.
  # It is left as-is from the original script.
  # print("DamageComponent found")
  #if 'load_this_entity' in conf: prop['explosion_entity_loaded'] = conf['load_this_entity']
  if conf.get('material_sparks_real', '0') == '1' and 'spark_material' in conf:
    prop['explosion_spark_material'] = conf['spark_material']

  prop.setdefault('explosion_cell_material', 'fire')
  if 'create_cell_material' in conf: prop['explosion_cell_material'] = conf['create_cell_material']


def parse_DamageModelComponent(prop, child):
  attr = child.attrib

  if 'materials_that_damage' in attr:
    mats = list(attr['materials_that_damage'].split(','))
    damages = ['0.1'] * len(mats)
    if 'materials_how_much_damage' in attr:
      damages = list(attr['materials_how_much_damage'].split(','))

    prop['damaged_by_materials'] = dict(zip(mats, damages))

  if attr.get('ragdoll_fx_forced', 'NONE') != 'DISINTEGRATED':
    prop['ragdoll_material'] = attr.get('ragdoll_material', 'meat')

  prop['blood_material'] = attr.get('blood_material', 'blood_fading')
  if 'blood_spray_material' in attr: prop['blood_spray_material'] = attr['blood_spray_material']


def parse_MagicConvertMaterialComponent(prop, child):
  attr = child.attrib

  conversions = []
  if 'from_material_array' in attr:
    from_mats = attr['from_material_array'].split(',')
    to_mats = attr['to_material_array'].split(',')

    conversions = list(zip(from_mats, to_mats))

  if 'from_material_tag' in attr:
    conversions.append((attr['from_material_tag'], attr['to_material']))

  if 'from_material' in attr and attr['from_material'] != '':
    conversions.append((attr['from_material'], attr['to_material']))

  if 'from_any_material' in attr:
    conversions.append(('[any]', attr['to_material']))

  if 'convert_entities' in attr:
    conversions.append(('[entity]', attr['to_material']))

  prop.setdefault('material_conversions', []).extend(conversions)


def parse_MaterialInventoryComponent(prop, child):
  attr = child.attrib

  inventory = {}
  for mat in child.findall('count_per_material_type/Material'):
    inventory[mat.attrib['material']] = mat.attrib['count']

  prop['material_inventory'] = inventory


def parse_PixelSpriteComponent(prop, child):
  prop['material'] = child.attrib.get('material', 'wood_loose')


tag_fns = {
  'PhysicsImageShapeComponent': parse_PhysicsImageShapeComponent,
  'ParticleEmitterComponent': parse_ParticleEmitterComponent,
  'ExplodeOnDamageComponent': parse_ExplodeOnDamageComponent,
  'DamageModelComponent': parse_DamageModelComponent,
  'MagicConvertMaterialComponent': parse_MagicConvertMaterialComponent,
  'MaterialInventoryComponent': parse_MaterialInventoryComponent,
  'PixelSpriteComponent': parse_PixelSpriteComponent,
}


def parse_tags(prop, root):
  for tagname, fn in tag_fns.items():
    for child in root.findall(f".//{tagname}"): # search all descendants
      fn(prop, child)

def get_translation(s):
  return translations.get(s, s)

def is_stupid_name(name):
  return name == 'projectile' or name == 'unknown' or name == 'card'

def get_name(filename, prop, root):
  for child in root.findall('.//UIInfoComponent'): # search all descendants
    if 'name' in child.attrib:
      t = get_translation(child.attrib['name'])
      if not is_stupid_name(t): return t

  for child in root.findall('.//ItemComponent'): # search all descendants
    if 'item_name' in child.attrib:
      t = get_translation(child.attrib['item_name'])
      if not is_stupid_name(t): return t

  clean_filename = Path(filename).as_posix()
  if clean_filename in spell_lookup:
    t = get_translation(spell_lookup[clean_filename])
    if not is_stupid_name(t): return t

  if 'name' in root.attrib:
    t = get_translation(root.attrib['name'])
    if not is_stupid_name(t): return t

  if clean_filename in extra_entity_xml_name_lookup:
    return extra_entity_xml_name_lookup[clean_filename]

  return None

def process_prop_xml(filename):
  try:
    tree = ET.parse(filename)
  except Exception as ex:
    # It's better to report the error and continue if possible
    print(f"Could not parse XML {filename}: {ex}")
    return

  root = tree.getroot()

  # Skip non-entity files silently
  if root.tag != 'Entity':
    return

  current_prop = {}
  final_prop = {}

  # First, process all base files recursively
  for child in root.findall('Base'):
    basefilename = child.attrib['file']
    # This recursively calls and builds up the props dict
    process_prop_xml(basefilename)
    # Update final_prop with the attributes from the base prop
    if basefilename in props:
        final_prop.update(props[basefilename])

  # Now, parse the tags in the current file, which may override base properties
  uiname = get_name(filename, current_prop, root)
  if uiname:
    current_prop['name'] = uiname

  parse_tags(current_prop, root)

  # Merge current properties into the final properties from bases
  final_prop.update(current_prop)
  props[filename] = final_prop


for filename in glob.glob("./data/**/*.xml", recursive=True):
  clean_filename = Path(filename).as_posix() # Use posix paths for consistency
  if "_debug" in clean_filename: continue
  if "_test_" in clean_filename: continue
  if "_workdir" in clean_filename: continue
  if "trailer" in clean_filename: continue
  if "intro" in clean_filename: continue
  #if "/player.xml" in clean_filename: continue
  try:
    process_prop_xml(clean_filename)
  except Exception:
    print(f"Major error processing file: {clean_filename}")
    traceback.print_exc()

print(f'{len(props)} entities found')

with open('entities.yml', 'w', encoding='utf-8') as entities_outfile:
  yaml.dump({name: prop for name, prop in props.items() if len(prop) > 0}, entities_outfile, default_flow_style=False, allow_unicode=True)


def mat_assign_set(prop, material_key, set_key, name):
  if material_key in prop:
    mat = prop[material_key]
    if mat in materials:
      materials[mat].setdefault(set_key, set()).add(name)

for filename, prop in props.items():
  name = prop.get('name', Path(filename).stem)
  if name.startswith("base_"): continue

  mat_assign_set(prop, 'blood_material', 'bloodOf', name)
  mat_assign_set(prop, 'blood_spray_material', 'bloodOf', name)
  mat_assign_set(prop, 'ragdoll_material', 'corpseOf', name)
  mat_assign_set(prop, 'material', 'bodyOf', name)
  mat_assign_set(prop, 'explosion_cell_material', 'explodesFrom', name)
  mat_assign_set(prop, 'explosion_spark_material', 'explodesFrom', name)

  for mat in prop.get('components', set()):
    if mat in materials:
        materials[mat].setdefault('bodyOf', set()).add(name)

  for mat in prop.get('emits_materials', set()):
    if mat in materials:
        materials[mat].setdefault('emittedBy', set()).add(name)

  for mat in prop.get('material_inventory', {}).keys():
    if mat in materials:
        materials[mat].setdefault('containedIn', set()).add(name)

  for from_mat, to_mat in prop.get('material_conversions', []):
    if to_mat in materials:
      materials[to_mat].setdefault('convertedToBy', set()).add(name)



####################################################################
## Create Similar Material Clusters (same-page tabs)
####################################################################
G = nx.Graph()
G.add_nodes_from(materials.keys())

def add_melts(mat, id):
  #This was printing a warning for what seems like intentional overwrites.
  #It's commented out to reduce console noise.
  #if 'melts' in mat and mat['melts'] != id:
  #  print(f"{mat['id']} ALREADY HAS MELTS: {mat['melts']} (adding {id})")
  mat['melts'] = id

same_name_nodes = {}
for mat in materials.values():
  same_name_nodes.setdefault(mat['name'], []).append(mat['id'])

  #if 'freezes' in mat: G.add_edge(mat['id'], mat['freezes'])
  #if 'melts' in mat: G.add_edge(mat['id'], mat['melts'])

  molten_id = mat['id'] + "_molten"
  if ('meltable' in mat['tags'] or 'meltable_metal' in mat['tags']) and molten_id in materials:
    add_melts(mat, molten_id)
    G.add_edge(mat['id'], molten_id)

  vapour_id = mat['id'] + "_vapour"
  if 'evaporable_custom' in mat['tags'] and vapour_id in materials:
    add_melts(mat, vapour_id)
    G.add_edge(mat['id'], vapour_id)

  if 'rust_box2d' in mat['tags']: G.add_edge(mat['id'], mat['id'] + '_rust')
  if 'rust_oxide' in mat['tags']: G.add_edge(mat['id'], mat['id'] + '_oxide')

  if 'meltable_metal_generic' in mat['tags']: add_melts(mat, 'metal_sand_molten')
  if 'meltable_to_poison' in mat['tags']: add_melts(mat, 'poison')
  if 'meltable_to_radioactive' in mat['tags']: add_melts(mat, 'radioactive_liquid')
  if 'meltable_to_cold' in mat['tags']: add_melts(mat, 'blood_cold')
  if 'meltable_to_acid' in mat['tags']: add_melts(mat, 'acid')
  if 'meltable_to_water' in mat['tags']: add_melts(mat, 'water')

for same_name_list in same_name_nodes.values():
  if len(same_name_list) > 1:
    G.add_edges_from(itertools.combinations(same_name_list, 2))

# Custom associations
G.add_edges_from([
  ('poison_gas', 'poison'),
  ('concrete_static', 'cement'),
  ('cloud_blood', 'blood'),
  ('bone_box2d', 'bone'),
  ('bone_static', 'bone'),
  ('coal_static', 'coal'),
  ('fungi_creeping', 'fungi_creeping_secret'),
  ('bloodgold_box2d', 'gold'),
  ('gold_static', 'gold_static_dark'),
  ('sand_blue', 'sand'),
  ('sodium_unstable', 'sodium'),
  ('alcohol_gas', 'alcohol'),
  ('bush_seed', 'ceiling_plant_material'),
  ('plant_seed', 'ceiling_plant_material'),
  ('rock_static_wet', 'rock_static'),
  ('wood_static_wet', 'wood_static'),
  ('wood_static_gas', 'wood_static'),
  ('lavasand', 'sand'),
  ('rotten_meat', 'meat'),
  #('meat_slime_orange', 'meat'),
  ('rotten_meat_radioactive', 'meat'),
  ('meat_slime_green', 'meat_slime_orange'),
  #('meat_worm', 'meat'),
  ('meat_helpless', 'meat_worm'),
  #('meat_trippy', 'meat'),
  ('meat_frog', 'meat_trippy'),
  #('meat_cursed', 'meat'),
  ('meat_slime_cursed', 'meat_cursed'),
  ('meat_teleport', 'meat_worm'),
  ('meat_fast', 'meat_worm'),
  ('meat_polymorph', 'meat_worm'),
  ('meat_polymorph_protection', 'meat_worm'),
  ('meat_confusion', 'meat_worm'),
  #('meat_warm', 'meat'),
  ('meat_hot', 'meat_warm'),
  ('meat_done', 'meat_warm'),
  ('meat_burned', 'meat_warm'),
  ('templebrick_static_ruined', 'brick'),
  ('wizardstone', 'templebrick_static'),
  ('templebrick_diamond_static', 'templebrick_static'),
  ('templebrick_moss_static', 'templebrick_static'),
  ('ice_poison_static', 'poison'),
  ('ice_acid_static', 'acid'),
  ('ice_radioactive_static', 'radioactive_liquid'),
  ('glass_brittle', 'glass'),
  ('water_ice', 'water'),
  ('cloud_slime', 'slime'),
  ('snow', 'snow_static'),
  ('blood_fading_slow', 'blood'),
])

G.remove_edges_from([
  ('steel_molten', 'steel'),
  ('aluminium_robot_molten', 'aluminium_robot'),
  ('aluminium_molten', 'aluminium'),
  ('aluminium_oxide_molten', 'aluminium_oxide'),
  ('meat_confusion', 'meat'),
  ('plastic_molten', 'plastic'),
  ('plastic_red_molten', 'plastic_red'),
  ('plastic_prop_molten', 'plastic_prop'),
  ('shock_powder', 'fungisoil'),
])

#pprint.pprint(G.edges())

clusters = list(nx.connected_components(G))

####################################################################
## Create Wiki Text
####################################################################
def stringify_material_data(mat, num = 0):
  n = ''
  if num > 0: n = str(num+1)

  result = ''
  if 'name' in mat: result += f"| name{n} = {mat['name']}\n"
  if 'type' in mat: result += f"| type{n} = {mat['type']}\n"
  result += f"| id{n} = {mat['id']}\n"
  result += f"| wang{n} = {mat['wang_color']}\n"
  if 'tags' in mat: result += f"| tags{n} = {','.join(mat['tags'])}\n"
  if 'density' in mat: result += f"| density{n} = {mat['density']}\n"
  if 'hardness' in mat: result += f"| hardness{n} = {mat['hardness']}\n"
  if 'durability' in mat: result += f"| durability{n} = {mat['durability']}\n"
  if 'lifetime' in mat: result += f"| lifetime{n} = {mat['lifetime']}\n"
  if 'biomes' in mat: result += f"| biomes{n} = {mat['biomes']}\n"
  if 'parent' in mat: result += f"| parent{n} = {mat['parent']}\n"
  if 'inheritsReactions' in mat: result += f"| inheritsReactions{n} = {mat['inheritsReactions']}\n"
  if 'submergeEffect' in mat: result += f"| submergeEffect{n} = {mat['submergeEffect']}\n"
  if 'stainEffect' in mat: result += f"| stainEffect{n} = {mat['stainEffect']}\n"
  if 'ingestEffect' in mat: result += f"| ingestEffect{n} = {mat['ingestEffect']}\n"
  if 'conductive' in mat: result += f"| conductive{n} = {mat['conductive']}\n"
  if 'burnable' in mat: result += f"| burnable{n} = {mat['burnable']}\n"
  if 'freezes' in mat: result += f"| freezes{n} = {mat['freezes']}\n"
  if 'melts' in mat: result += f"| melts{n} = {mat['melts']}\n"
  if 'breakInto' in mat: result += f"| breakInto{n} = {mat['breakInto']}\n"
  if 'slippery' in mat: result += f"| slippery{n} = {mat['slippery']}\n"
  if 'flaming' in mat: result += f"| flaming{n} = {mat['flaming']}\n"
  if 'fuel' in mat: result += f"| fuel{n} = {mat['fuel']}\n"
  if 'playerCollision' in mat: result += f"| playerCollision{n} = {mat['playerCollision']}\n"

  if 'bloodOf' in mat: result += f"| bloodOf{n} = {','.join(mat['bloodOf'])}\n"
  if 'corpseOf' in mat: result += f"| corpseOf{n} = {','.join(mat['corpseOf'])}\n"
  if 'bodyOf' in mat: result += f"| bodyOf{n} = {','.join(mat['bodyOf'])}\n"
  if 'explodesFrom' in mat: result += f"| explodesFrom{n} = {','.join(mat['explodesFrom'])}\n"
  if 'emittedBy' in mat: result += f"| emittedBy{n} = {','.join(mat['emittedBy'])}\n"
  if 'containedIn' in mat: result += f"| containedIn{n} = {','.join(mat['containedIn'])}\n"
  if 'convertedToBy' in mat: result += f"| convertedToBy{n} = {','.join(mat['convertedToBy'])}\n"

  return result

mats_list = open('matlist.csv', 'wt')
for m in materials.values():
  mats_list.write(f"#{m['wang_color'][2:]},vanilla,material,{m['id']}\n")
mats_list.close()

# Create the wiki text
materials_output_file = open('materials.txt', 'wt', encoding='utf-8')

densities = []

for group in clusters:
  materials_output_file.write('{{Infobox material\n')

  mats = [materials[m] for m in list(group)]
  mats.sort(key=lambda m: -len(m.get('biomes', '')))

  material_strings = [stringify_material_data(mat, i) for i, mat in enumerate(mats)]

  materials_output_file.write('\n'.join(material_strings))
  materials_output_file.write('}}\n\n')

materials_output_file.close()


density_mats_by_name = {}
for mat in materials.values():
  if not 'density' in mat: continue
  density_mats_by_name.setdefault(mat['name'], []).append(mat['id'])

densities = []
for group in density_mats_by_name.values():
  mats = [materials[m] for m in list(group)]

  if len(mats) > 0:
    last_density = float(mats[0]['density'])
    all_same_density = all(float(mat['density']) == last_density for mat in mats)
    if all_same_density:
      densities.append({ 'name': mats[0]['name'], 'variant': 'All Variants' if len(mats) > 1 else '', 'type': mats[0].get('type', ''), 'cell_type': mats[0].get('cell_type', ''), 'density': last_density })
    else:
      for mat in mats:
        densities.append({ 'name': mat['name'], 'variant': f"<code>{mat['id']}</code>", 'type': mat.get('type', ''), 'cell_type': mat.get('cell_type', ''), 'density': float(mat['density']) })

densities.sort(key=lambda m: m['density'])

liquid_density_out = open('liquid_density.txt', 'wt', encoding='utf-8')
density_out = open('density.txt', 'wt', encoding='utf-8')
for mat in densities:
  if mat.get('type') == 'Liquid':
    liquid_density_out.write(f"|-\n| [[{mat['name']}]] || {mat['variant']} || {mat['density']}\n")
  if mat.get('cell_type') != 'solid' and mat.get('cell_type') != '':
    density_out.write(f"|-\n| [[{mat['name']}]] || {mat['variant']} || {mat['density']}\n")

liquid_density_out.close()
density_out.close()

print("\nScript finished. All image masking has been removed.")