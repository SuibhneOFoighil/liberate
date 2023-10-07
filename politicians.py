from elevenlabs import VoiceSettings
POLITICIANS = {
    'Donald Trump': {
        'avatar': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Donald_Trump_official_portrait.jpg/1280px-Donald_Trump_official_portrait.jpg',
        'intro': "Donald John Trump is an American politician, media personality, and businessman who served as the 45th president of the United States from 2017 to 2021. Trump graduated from the University of Pennsylvania with a bachelor's degree in economics in 1968. He became president of his father's real-estate business in 1971 and renamed it the Trump Organization. He expanded its operations to building and renovating skyscrapers, hotels, casinos, and golf courses and later started side ventures, mostly by licensing his name. From 2004 to 2015, he co-produced and hosted the reality television series The Apprentice. He and his businesses have been plaintiff or defendant in more than 4,000 state and federal legal actions, including six business bankruptcies.",
        'shortcode': 'dt',
        'voice_id': 'dcjrIobr206WwW0QyfzA',
        'voice_settings': VoiceSettings(stability=0.5, similarity_boost=1, style=0, use_speaker_boost=True)
    },
    'Joe Biden': {
        'avatar': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Joe_Biden_presidential_portrait.jpg/1280px-Joe_Biden_presidential_portrait.jpg',
        'intro': "Joseph Robinette Biden Jr. is an American politician who is the 46th and current president of the United States. A member of the Democratic Party, he previously served as the 47th vice president from 2009 to 2017 under President Barack Obama and represented Delaware in the United States Senate from 1973 to 2009.",
        'shortcode': 'jb',
        'voice_id': '0loF9RbzemuMZWmj3o3W',
        'voice_settings':VoiceSettings(stability=0.5, similarity_boost=0.5, style=0, use_speaker_boost=True)
    },
    'Alexandria Ocasio-Cortez': {
        'avatar': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Alexandria_Ocasio-Cortez_Official_Portrait.jpg/1280px-Alexandria_Ocasio-Cortez_Official_Portrait.jpg',
        'intro': "Alexandria Ocasio-Cortez, also known by her initials AOC, is an American politician and activist. She has served as the U.S. representative for New York's 14th congressional district since 2019, as a member of the Democratic Party. The district includes the eastern part of the Bronx, portions of north-central Queens, and Rikers Island in New York City",
        'shortcode': 'aoc',
        'voice_id': 'qc3Ba10ePIFCj8oqvalO',
        'voice_settings': VoiceSettings(stability=0.5, similarity_boost=0.5, style=0, use_speaker_boost=True)
    },
    'J.D. Vance': {
        'avatar': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Senator_Vance_official_portrait._118th_Congress.jpg/1280px-Senator_Vance_official_portrait._118th_Congress.jpg',
        'intro': "James David Vance is an American venture capitalist, author, and the junior United States senator from Ohio since 2023. A member of the Republican Party, he came to prominence with his 2016 memoir, Hillbilly Elegy.",
        'shortcode': 'jdv',
        'voice_id': 'qrNf9kQtbODftmFjF9ji',
        'voice_settings': VoiceSettings(stability=0.5, similarity_boost=0.5, style=0, use_speaker_boost=True)
    },
    'Marjorie Taylor Greene': {
        'avatar': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Marjorie_Taylor_Greene_117th_Congress_portrait.jpeg/1280px-Marjorie_Taylor_Greene_117th_Congress_portrait.jpeg',
        'intro': "Marjorie Taylor Greene, also known by her initials MTG, is an American far-right politician, businesswoman, and conspiracy theorist who has been the U.S. representative for Georgia's 14th congressional district since 2021. A member of the Republican Party, she was elected to Congress in 2020 following the retirement of Republican incumbent Tom Graves, and reelected in 2022.",
        'shortcode': 'mtg',
        'voice_id': 'eBUkC3bUylhtUJhhmPtT',
        'voice_settings': VoiceSettings(stability=0.5, similarity_boost=1, style=0, use_speaker_boost=True)
    },
    'Vivek Ramaswamy': {
        'avatar': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Vivek_Ramaswamy_by_Gage_Skidmore.jpg/1280px-Vivek_Ramaswamy_by_Gage_Skidmore.jpg',
        'intro': 'Vivek Ramaswamy is a biotech entrepreneur and conservative author. He was born in 1985 in Ohio to Indian Hindu parents. He graduated from Harvard with a BA in biology in 2007 and from Yale Law School in 2013. He worked at a hedge fund before founding a biopharmaceutical company, Roivant Sciences, in 2014, and an investment firm, Strive Asset Management, in 2021. He wrote Woke, Inc., a critique of businesses that have sought to be more socially aware, and announced his candidacy for the 2024 GOP presidential nomination in February 2023.',
        'shortcode': 'vr',
        'voice_id': 'lAZKsjhcbMmadBhSMtZk',
        'voice_settings': VoiceSettings(stability=0.3, similarity_boost=1, style=0.05, use_speaker_boost=True)
    },
    'Barack Obama': {
        'avatar': 'https://upload.wikimedia.org/wikipedia/commons/8/8d/President_Barack_Obama.jpg',
        'intro': 'Barack Hussein Obama II is an American politician who served as the 44th president of the United States from 2009 to 2017. A member of the Democratic Party, he was the first African-American president. Obama previously served as a U.S. senator representing Illinois from 2005 to 2008 and as an Illinois state senator from 1997 to 2004, and worked as a civil rights lawyer and university lecturer.',
        'shortcode': 'bo',
        'voice_id': 'Z5mRuhG3QytKpJ6joH8k',
        'voice_settings': VoiceSettings(stability=0.4, similarity_boost=0.5, style=0, use_speaker_boost=True)
    },
    'Gretchen Whitmer': {
        'avatar': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Gretchen_Whitmer_%282021%29_%28cropped%29.jpg/1280px-Gretchen_Whitmer_%282021%29_%28cropped%29.jpg',
        'intro': "Gretchen Esther Whitmer is an American lawyer and politician serving as the 49th governor of Michigan since 2019. A member of the Democratic Party, she served in the Michigan House of Representatives from 2001 to 2006 and in the Michigan Senate from 2006 to 2015.",
        'shortcode': 'gw',
        'voice_id': 'Au5Rhs22w1V4Z8idLNxu',
        'voice_settings': VoiceSettings(stability=0.5, similarity_boost=1, style=0, use_speaker_boost=True)
    }
}

def get_politician_by_shortcode(shortcode):
    for name, info in POLITICIANS.items():
        if info["shortcode"] == shortcode:
            return name
    return None

