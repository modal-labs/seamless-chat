export interface Message {
    messageId: string;
    userId: string;
    userName: string;
    lang: string;
    text: string;
    audio: number[];
}

export interface User {
    name: string;
    lang: string;
}

export interface Room {
    name: string;
    members: string[];
}

export const languageOptions = [
    {
        name: 'modern standard arabic',
        code: 'arb'
    },
    {
        name: 'bengali',
        code: 'ben'
    },
    {
        name: 'catalan',
        code: 'cat'
    },
    {
        name: 'czech',
        code: 'ces'
    },
    {
        name: 'mandarin chinese',
        code: 'cmn'
    },
    {
        name: 'welsh',
        code: 'cym'
    },
    {
        name: 'danish',
        code: 'dan'
    },
    {
        name: 'german',
        code: 'deu'
    },
    {
        name: 'english',
        code: 'eng'
    },
    {
        name: 'estonian',
        code: 'est'
    },
    {
        name: 'french',
        code: 'fra'
    },
    {
        name: 'hindi',
        code: 'hin'
    },
    {
        name: 'indonesian',
        code: 'ind'
    },
    {
        name: 'italian',
        code: 'ita'
    },
    {
        name: 'japanese',
        code: 'jpn'
    },
    {
        name: 'korean',
        code: 'kor'
    },
    {
        name: 'dutch',
        code: 'nld'
    },
    {
        name: 'polish',
        code: 'pol'
    },
    {
        name: 'portuguese',
        code: 'por'
    },
    {
        name: 'romanian',
        code: 'ron'
    },
    {
        name: 'russian',
        code: 'rus'
    },
    {
        name: 'slovak',
        code: 'slk'
    },
    {
        name: 'spanish',
        code: 'spa'
    },
    {
        name: 'swedish',
        code: 'swe'
    },
    {
        name: 'telugu',
        code: 'tel'
    },
    {
        name: 'thai',
        code: 'tha'
    },
    {
        name: 'turkish',
        code: 'tur'
    },
    {
        name: 'ukrainian',
        code: 'ukr'
    },
    {
        name: 'urdu',
        code: 'urd'
    },
    {
        name: 'uzbek',
        code: 'uzn'
    },
    {
        name: 'vietnamese',
        code: 'vie'
    }
];
