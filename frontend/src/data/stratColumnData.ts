/**
 * Simplified stratigraphic column data for each basin.
 * Ordered top (youngest) to bottom (oldest).
 * Lithology patterns: tuff, sandstone, mudstone, limestone, granite, basalt, etc.
 */

export interface StratUnit {
  formation: string;
  ageRange: [number, number]; // [young, old] in Ma
  lithology: string;
  color: string;
  thickness?: number; // relative thickness for display (default 1)
}

export const BASIN_STRAT: Record<string, {
  name: string;
  nameCn: string;
  units: StratUnit[];
}> = {
  "滦平盆地": {
    name: "Luanping Basin",
    nameCn: "滦平盆地",
    units: [
      { formation: "土城子组", ageRange: [145, 152], lithology: "砂岩/砾岩", color: "#c9a96e" },
      { formation: "张家口组", ageRange: [134.8, 145], lithology: "流纹质凝灰岩", color: "#d4a574", thickness: 1.5 },
      { formation: "大北沟组", ageRange: [130, 134.4], lithology: "砂质凝灰岩", color: "#b8956a" },
      { formation: "义县组", ageRange: [122, 130], lithology: "安山岩/玄武岩", color: "#7a6b5a" },
    ],
  },
  "松辽盆地": {
    name: "Songliao Basin",
    nameCn: "松辽盆地",
    units: [
      { formation: "泉头组", ageRange: [88, 100], lithology: "砂岩/泥岩", color: "#a8c4a0" },
      { formation: "登楼库组", ageRange: [100, 108], lithology: "砂岩", color: "#c9b896" },
      { formation: "营城组", ageRange: [113.5, 120], lithology: "流纹岩", color: "#d4907a" },
      { formation: "沙河子组", ageRange: [120, 130], lithology: "砂泥岩", color: "#b0a090" },
      { formation: "龙江组", ageRange: [122.3, 135], lithology: "安山岩", color: "#8a7a6a" },
    ],
  },
  "海拉尔盆地": {
    name: "Hailar Basin",
    nameCn: "海拉尔盆地",
    units: [
      { formation: "伊敏组", ageRange: [125, 135], lithology: "凝灰岩/煤系", color: "#90a080" },
      { formation: "大磨拐河组", ageRange: [135, 145], lithology: "砂泥岩", color: "#b0a890" },
      { formation: "满克头鄂博组", ageRange: [150, 165], lithology: "花岗岩/凝灰岩", color: "#d4a0a0" },
    ],
  },
  "天台盆地": {
    name: "Tiantai Basin",
    nameCn: "天台盆地",
    units: [
      { formation: "赖家组", ageRange: [72, 85], lithology: "砂岩/泥岩", color: "#c0b890" },
      { formation: "赤城山组", ageRange: [88, 96], lithology: "晶屑凝灰岩", color: "#d4956a" },
      { formation: "馆头组", ageRange: [100, 115], lithology: "砂岩", color: "#b8a878" },
    ],
  },
  "准噶尔盆地": {
    name: "Junggar Basin",
    nameCn: "准噶尔盆地",
    units: [
      { formation: "吐谷鲁群", ageRange: [100, 145], lithology: "砂岩（碎屑锆石）", color: "#c8b890" },
      { formation: "齐古组", ageRange: [160, 170], lithology: "凝灰岩", color: "#a0b0a0" },
      { formation: "头屯河组", ageRange: [165, 175], lithology: "砂岩/泥岩", color: "#b0a070" },
    ],
  },
  "鄂尔多斯盆地": {
    name: "Ordos Basin",
    nameCn: "鄂尔多斯盆地",
    units: [
      { formation: "延长组", ageRange: [230, 240], lithology: "砂岩/泥岩", color: "#a0b090", thickness: 2 },
      { formation: "纸坊组", ageRange: [240, 245], lithology: "砂岩", color: "#c0a870" },
    ],
  },
  "四川盆地": {
    name: "Sichuan Basin",
    nameCn: "四川盆地",
    units: [
      { formation: "自流井组", ageRange: [165, 175], lithology: "泥灰岩", color: "#90a0b0" },
      { formation: "沙溪庙组", ageRange: [160, 165], lithology: "砂岩/泥岩", color: "#b0a878" },
    ],
  },
  "二连盆地": {
    name: "Erlian Basin",
    nameCn: "二连盆地",
    units: [
      { formation: "阿尔善组", ageRange: [125, 135], lithology: "玄武岩", color: "#5a6a5a" },
      { formation: "腾格尔组", ageRange: [120, 125], lithology: "砂泥岩", color: "#a0988a" },
    ],
  },
  "渤海湾盆地": {
    name: "Bohai Bay Basin",
    nameCn: "渤海湾盆地",
    units: [
      { formation: "东营组", ageRange: [28, 38], lithology: "砂泥岩", color: "#a0c0a0" },
      { formation: "沙河街组", ageRange: [38, 50], lithology: "泥岩/砂岩", color: "#80a080", thickness: 2 },
      { formation: "孔店组", ageRange: [50, 65], lithology: "砂砾岩", color: "#c0a870" },
    ],
  },
  "沁水盆地": {
    name: "Qinshui Basin",
    nameCn: "沁水盆地",
    units: [
      { formation: "太原组", ageRange: [298, 310], lithology: "石灰岩/煤系", color: "#404040", thickness: 1.5 },
      { formation: "山西组", ageRange: [290, 298], lithology: "砂岩/煤系", color: "#606050" },
    ],
  },
  "天台盆地2": {
    name: "Tiantai",
    nameCn: "天台盆地",
    units: [], // handled by 天台盆地
  },
  "楚雄盆地": {
    name: "Chuxiong Basin",
    nameCn: "楚雄盆地",
    units: [
      { formation: "妥甸组", ageRange: [108, 118], lithology: "泥岩", color: "#8a9a80" },
      { formation: "高峰寺组", ageRange: [118, 130], lithology: "砂岩", color: "#b0a878" },
    ],
  },
  "鄱阳盆地": {
    name: "Poyang Basin",
    nameCn: "鄱阳盆地",
    units: [
      { formation: "莲荷组", ageRange: [93, 100], lithology: "凝灰岩", color: "#d0a878" },
      { formation: "石溪组", ageRange: [100, 110], lithology: "砂泥岩", color: "#a09880" },
    ],
  },
  "塔里木盆地": {
    name: "Tarim Basin",
    nameCn: "塔里木盆地",
    units: [
      { formation: "库车组", ageRange: [5, 23], lithology: "砂砾岩（碎屑锆石）", color: "#d0c090", thickness: 2 },
      { formation: "吉迪克组", ageRange: [23, 35], lithology: "砂泥岩", color: "#b0a878" },
    ],
  },
  "柴达木盆地": {
    name: "Qaidam Basin",
    nameCn: "柴达木盆地",
    units: [
      { formation: "路乐河组", ageRange: [30, 55], lithology: "砂岩（碎屑锆石）", color: "#c0b890", thickness: 2 },
      { formation: "干柴沟组", ageRange: [23, 30], lithology: "泥岩/砂岩", color: "#a09878" },
    ],
  },
  "江汉盆地": {
    name: "Jianghan Basin",
    nameCn: "江汉盆地",
    units: [
      { formation: "五龙组", ageRange: [90, 100], lithology: "粉砂岩", color: "#b0b090" },
      { formation: "渔洋组", ageRange: [80, 90], lithology: "砂泥岩", color: "#a0a880" },
    ],
  },
};
