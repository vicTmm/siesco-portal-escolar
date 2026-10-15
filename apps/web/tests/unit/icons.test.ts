import {describe,it,expect} from "vitest";
import {moduleIcons} from "../../src/lib/icons";
describe("iconografia dos destinos",()=>{it("usa um símbolo distinto para cada destino",()=>{const icons=Object.values(moduleIcons);expect(new Set(icons).size).toBe(icons.length);});});
