/**
 * ICS International Chronostratigraphic Chart — Stage-level definitions.
 * Source: user-provided chronostratigraphic data (标准地层图.txt)
 * startMa = older (bottom) boundary, endMa = younger (top) boundary.
 */

export interface IcsStage {
  name: string;
  startMa: number;
  endMa: number;
  color: string;
  period: string;
}

export const ICS_STAGES: IcsStage[] = [
  // ── Cambrian ──
  { name: "Fortunian",  startMa: 538.8,  endMa: 529,  color: "#99B575",  period: "Cambrian" },
  { name: "Stage 2",  startMa: 529,  endMa: 521,  color: "#A6BA80",  period: "Cambrian" },
  { name: "Stage 3",  startMa: 521,  endMa: 514.5,  color: "#A6C583",  period: "Cambrian" },
  { name: "Stage 4",  startMa: 514.5,  endMa: 506.5,  color: "#B3CA8E",  period: "Cambrian" },
  { name: "Wuliuan",  startMa: 506.5,  endMa: 504.5,  color: "#B3D492",  period: "Cambrian" },
  { name: "Drumian",  startMa: 504.5,  endMa: 500.5,  color: "#BFD99D",  period: "Cambrian" },
  { name: "Guzhangian",  startMa: 500.5,  endMa: 497,  color: "#CCDFAA",  period: "Cambrian" },
  { name: "Paibian",  startMa: 497,  endMa: 494.2,  color: "#CCEBAE",  period: "Cambrian" },
  { name: "Jiangshanian",  startMa: 494.2,  endMa: 491,  color: "#D9F0BB",  period: "Cambrian" },
  { name: "Stage 10",  startMa: 491,  endMa: 486.85,  color: "#E6F5C9",  period: "Cambrian" },

  // ── Ordovician ──
  { name: "Tremadocian",  startMa: 486.85,  endMa: 477.1,  color: "#33A97E",  period: "Ordovician" },
  { name: "Floian",  startMa: 477.1,  endMa: 471.3,  color: "#41B087",  period: "Ordovician" },
  { name: "Dapingian",  startMa: 471.3,  endMa: 469.4,  color: "#66C092",  period: "Ordovician" },
  { name: "Darriwilian",  startMa: 469.4,  endMa: 458.2,  color: "#74C69C",  period: "Ordovician" },
  { name: "Sandbian",  startMa: 458.2,  endMa: 452.8,  color: "#8CD094",  period: "Ordovician" },
  { name: "Katian",  startMa: 452.8,  endMa: 445.2,  color: "#99D69F",  period: "Ordovician" },
  { name: "Hirnantian",  startMa: 445.2,  endMa: 443.1,  color: "#A6DBAB",  period: "Ordovician" },

  // ── Silurian ──
  { name: "Rhuddanian",  startMa: 443.1,  endMa: 440.5,  color: "#A6DCB5",  period: "Silurian" },
  { name: "Aeronian",  startMa: 440.5,  endMa: 438.6,  color: "#B3E1C2",  period: "Silurian" },
  { name: "Telychian",  startMa: 438.6,  endMa: 432.9,  color: "#BFE6CF",  period: "Silurian" },
  { name: "Sheinwoodian",  startMa: 432.9,  endMa: 430.6,  color: "#BFE6C3",  period: "Silurian" },
  { name: "Homerian",  startMa: 430.6,  endMa: 426.7,  color: "#CCEBD1",  period: "Silurian" },
  { name: "Gorstian",  startMa: 426.7,  endMa: 425,  color: "#CCECDD",  period: "Silurian" },
  { name: "Ludfordian",  startMa: 425,  endMa: 422.7,  color: "#D9F0DF",  period: "Silurian" },
  { name: "Pridoli",  startMa: 422.7,  endMa: 419.62,  color: "#E6F5E1",  period: "Silurian" },

  // ── Devonian ──
  { name: "Lochkovian",  startMa: 419.62,  endMa: 413.02,  color: "#E5B75A",  period: "Devonian" },
  { name: "Pragian",  startMa: 413.02,  endMa: 410.62,  color: "#E5C468",  period: "Devonian" },
  { name: "Emsian",  startMa: 410.62,  endMa: 393.47,  color: "#E5D075",  period: "Devonian" },
  { name: "Eifelian",  startMa: 393.47,  endMa: 387.95,  color: "#F1D576",  period: "Devonian" },
  { name: "Givetian",  startMa: 387.95,  endMa: 382.31,  color: "#F1E185",  period: "Devonian" },
  { name: "Frasnian",  startMa: 382.31,  endMa: 372.15,  color: "#F2EDAD",  period: "Devonian" },
  { name: "Famennian",  startMa: 372.15,  endMa: 358.86,  color: "#F2EDC5",  period: "Devonian" },

  // ── Carboniferous ──
  { name: "Tournaisian",  startMa: 358.86,  endMa: 346.7,  color: "#8CB06C",  period: "Carboniferous" },
  { name: "Visean",  startMa: 346.7,  endMa: 330.3,  color: "#A6B96C",  period: "Carboniferous" },
  { name: "Serpukhovian",  startMa: 330.3,  endMa: 323.4,  color: "#BFC26B",  period: "Carboniferous" },
  { name: "Bashkirian",  startMa: 323.4,  endMa: 315.2,  color: "#99C2B5",  period: "Carboniferous" },
  { name: "Moscovian",  startMa: 315.2,  endMa: 307,  color: "#C7CBB9",  period: "Carboniferous" },
  { name: "Kasimovian",  startMa: 307,  endMa: 303.7,  color: "#BFD0C5",  period: "Carboniferous" },
  { name: "Gzhelian",  startMa: 303.7,  endMa: 298.9,  color: "#CCD4C7",  period: "Carboniferous" },

  // ── Permian ──
  { name: "Asselian",  startMa: 298.9,  endMa: 293.52,  color: "#E36350",  period: "Permian" },
  { name: "Sakmarian",  startMa: 293.52,  endMa: 290.1,  color: "#E36F5C",  period: "Permian" },
  { name: "Artinskian",  startMa: 290.1,  endMa: 283.3,  color: "#E37B68",  period: "Permian" },
  { name: "Kungurian",  startMa: 283.3,  endMa: 274.4,  color: "#E38776",  period: "Permian" },
  { name: "Roadian",  startMa: 274.4,  endMa: 266.9,  color: "#FB8069",  period: "Permian" },
  { name: "Wordian",  startMa: 266.9,  endMa: 264.28,  color: "#FB8D76",  period: "Permian" },
  { name: "Capitanian",  startMa: 264.28,  endMa: 259.51,  color: "#FB9A85",  period: "Permian" },
  { name: "Wuchiapingian",  startMa: 259.51,  endMa: 254.14,  color: "#FCB4A2",  period: "Permian" },
  { name: "Changhsingian",  startMa: 254.14,  endMa: 251.902,  color: "#FCC0B2",  period: "Permian" },

  // ── Triassic ──
  { name: "Induan",  startMa: 251.902,  endMa: 249.9,  color: "#A4469F",  period: "Triassic" },
  { name: "Olenekian",  startMa: 249.9,  endMa: 246.7,  color: "#B051A5",  period: "Triassic" },
  { name: "Anisian",  startMa: 246.7,  endMa: 241.464,  color: "#BC75B7",  period: "Triassic" },
  { name: "Ladinian",  startMa: 241.464,  endMa: 237,  color: "#C983BF",  period: "Triassic" },
  { name: "Carnian",  startMa: 237,  endMa: 227.3,  color: "#C99BCB",  period: "Triassic" },
  { name: "Norian",  startMa: 227.3,  endMa: 205.7,  color: "#D6AAD3",  period: "Triassic" },
  { name: "Rhaetian",  startMa: 205.7,  endMa: 201.4,  color: "#E3B9DB",  period: "Triassic" },

  // ── Jurassic ──
  { name: "Hettangian",  startMa: 201.4,  endMa: 199.5,  color: "#4EB3D3",  period: "Jurassic" },
  { name: "Sinemurian",  startMa: 199.5,  endMa: 192.9,  color: "#67BCD8",  period: "Jurassic" },
  { name: "Pliensbachian",  startMa: 192.9,  endMa: 184.2,  color: "#80C5DD",  period: "Jurassic" },
  { name: "Toarcian",  startMa: 184.2,  endMa: 174.7,  color: "#99CEE3",  period: "Jurassic" },
  { name: "Aalenian",  startMa: 174.7,  endMa: 170.9,  color: "#9AD9DD",  period: "Jurassic" },
  { name: "Bajocian",  startMa: 170.9,  endMa: 168.2,  color: "#A6DDE0",  period: "Jurassic" },
  { name: "Bathonian",  startMa: 168.2,  endMa: 165.3,  color: "#B3E2E3",  period: "Jurassic" },
  { name: "Callovian",  startMa: 165.3,  endMa: 161.5,  color: "#BFE7E5",  period: "Jurassic" },
  { name: "Oxfordian",  startMa: 161.5,  endMa: 154.8,  color: "#BFE7F1",  period: "Jurassic" },
  { name: "Kimmeridgian",  startMa: 154.8,  endMa: 149.2,  color: "#CCECF4",  period: "Jurassic" },
  { name: "Tithonian",  startMa: 149.2,  endMa: 143.1,  color: "#D9F1F7",  period: "Jurassic" },

  // ── Cretaceous ──
  { name: "Berriasian",  startMa: 143.1,  endMa: 137.05,  color: "#8CCD60",  period: "Cretaceous" },
  { name: "Valanginian",  startMa: 137.05,  endMa: 132.6,  color: "#99D36A",  period: "Cretaceous" },
  { name: "Hauterivian",  startMa: 132.6,  endMa: 125.77,  color: "#A6D975",  period: "Cretaceous" },
  { name: "Barremian",  startMa: 125.77,  endMa: 121.4,  color: "#B3DF7F",  period: "Cretaceous" },
  { name: "Aptian",  startMa: 121.4,  endMa: 113.2,  color: "#BFE48A",  period: "Cretaceous" },
  { name: "Albian",  startMa: 113.2,  endMa: 100.5,  color: "#CCEA97",  period: "Cretaceous" },
  { name: "Cenomanian",  startMa: 100.5,  endMa: 93.9,  color: "#B3DE53",  period: "Cretaceous" },
  { name: "Turonian",  startMa: 93.9,  endMa: 89.8,  color: "#BFE35D",  period: "Cretaceous" },
  { name: "Coniacian",  startMa: 89.8,  endMa: 85.7,  color: "#CCE968",  period: "Cretaceous" },
  { name: "Santonian",  startMa: 85.7,  endMa: 83.6,  color: "#D9EF74",  period: "Cretaceous" },
  { name: "Campanian",  startMa: 83.6,  endMa: 72.2,  color: "#E6F47F",  period: "Cretaceous" },
  { name: "Maastrichtian",  startMa: 72.2,  endMa: 66,  color: "#F2FA8C",  period: "Cretaceous" },

  // ── Paleogene ──
  { name: "Danian",  startMa: 66,  endMa: 61.66,  color: "#FDB462",  period: "Paleogene" },
  { name: "Selandian",  startMa: 61.66,  endMa: 59.24,  color: "#FEBF65",  period: "Paleogene" },
  { name: "Thanetian",  startMa: 59.24,  endMa: 56,  color: "#FDBF6F",  period: "Paleogene" },
  { name: "Ypresian",  startMa: 56,  endMa: 48.07,  color: "#FCA773",  period: "Paleogene" },
  { name: "Lutetian",  startMa: 48.07,  endMa: 41.03,  color: "#FCB482",  period: "Paleogene" },
  { name: "Bartonian",  startMa: 41.03,  endMa: 37.71,  color: "#FDC091",  period: "Paleogene" },
  { name: "Priabonian",  startMa: 37.71,  endMa: 33.9,  color: "#FDCDA1",  period: "Paleogene" },
  { name: "Rupelian",  startMa: 33.9,  endMa: 27.3,  color: "#FED99A",  period: "Paleogene" },
  { name: "Chattian",  startMa: 27.3,  endMa: 23.04,  color: "#FEE6AA",  period: "Paleogene" },

  // ── Neogene ──
  { name: "Aquitanian",  startMa: 23.04,  endMa: 20.45,  color: "#FFFF33",  period: "Neogene" },
  { name: "Burdigalian",  startMa: 20.45,  endMa: 15.98,  color: "#FFFF41",  period: "Neogene" },
  { name: "Langhian",  startMa: 15.98,  endMa: 13.82,  color: "#FFFF4D",  period: "Neogene" },
  { name: "Serravallian",  startMa: 13.82,  endMa: 11.63,  color: "#FFFF59",  period: "Neogene" },
  { name: "Tortonian",  startMa: 11.63,  endMa: 7.246,  color: "#FFFF66",  period: "Neogene" },
  { name: "Messinian",  startMa: 7.246,  endMa: 5.333,  color: "#FFFF73",  period: "Neogene" },
  { name: "Zanclean",  startMa: 5.333,  endMa: 3.6,  color: "#FFFFB3",  period: "Neogene" },
  { name: "Piacenzian",  startMa: 3.6,  endMa: 2.58,  color: "#FFFFBF",  period: "Neogene" },

  // ── Quaternary ──
  { name: "Gelasian",  startMa: 2.58,  endMa: 1.8,  color: "#FFEDB3",  period: "Quaternary" },
  { name: "Calabrian",  startMa: 1.8,  endMa: 0.774,  color: "#FFF2C7",  period: "Quaternary" },
  { name: "Chibanian",  startMa: 0.774,  endMa: 0.129,  color: "#FFF2C7",  period: "Quaternary" },
  { name: "Late Pleistocene",  startMa: 0.129,  endMa: 0.0117,  color: "#FFF2C7",  period: "Quaternary" },
  { name: "Greenlandian",  startMa: 0.0117,  endMa: 0.0082,  color: "#FEF2E0",  period: "Quaternary" },
  { name: "Northgrippian",  startMa: 0.0082,  endMa: 0.0042,  color: "#FEF2E0",  period: "Quaternary" },
  { name: "Meghalayan",  startMa: 0.0042,  endMa: 0,  color: "#FEF2E0",  period: "Quaternary" },
];

/** Given an age in Ma, find the ICS stage it belongs to. */
export function findStage(ageMa: number): IcsStage | undefined {
  return ICS_STAGES.find((s) => ageMa >= s.endMa && ageMa < s.startMa);
}

/** Get stages within an age range. */
export function getStagesInRange(startMa: number, endMa: number): IcsStage[] {
  return ICS_STAGES.filter((s) => s.startMa > endMa && s.endMa < startMa);
}
