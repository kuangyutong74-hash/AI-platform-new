import {readFileSync,writeFileSync} from "node:fs";
const replacements={
  "modules/talent-report/src/components/book/pages/AdviceSpread.vue":[["GROWING TOGETHER · 09","GROWING TOGETHER · 10"]],
  "modules/talent-report/src/components/book/BookPagination.vue":[["v-for=\"n in 9\"","v-for=\"n in 10\""]],
  "modules/talent-report/src/components/MagicBook.vue":[["useBookFlip(9)","useBookFlip(10)"],["currentSpread.value===8","currentSpread.value===9"],["currentSpread<8","currentSpread<9"],[" / 9 跨页"," / 10 跨页"]],
  "modules/talent-report/src/components/MagicBook.vue":[["useBookFlip(9)","useBookFlip(10)"],["currentSpread.value===8","currentSpread.value===9"],["currentSpread<8","currentSpread<9"],[" / 9 跨页"," / 10 跨页"],["@finish=\"closeBook\"","@finish=\"closeBook\" @reflection-complete=\"finishReflection\" @reflection-skip=\"finishReflection()\""]],
};
for(const [path,pairs] of Object.entries(replacements)){let source=readFileSync(path,"utf8");for(const [from,to] of pairs)source=source.replaceAll(from,to);writeFileSync(path,source,"utf8")}
