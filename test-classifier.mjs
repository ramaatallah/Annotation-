
import { classifyEntity } from "./src/content/entity-classifier.js";

const entities = [
  { text: "جامعة النجاح الوطنية", type: "ORGANIZATION" },
  { text: "وزارة الصحة", type: "ORGANIZATION" },
  { text: "مستشفى رفيديا", type: "ORGANIZATION" },
  { text: "نابلس", type: "LOCATION" },
];

console.table(entities.map(classifyEntity));
