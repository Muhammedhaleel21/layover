// Curated Kozhikode data. Coordinates are approximate; travel/visit/cost values are conservative
// estimates, NOT live transport data. VERIFY facts + coordinates on-site before the demo.
export type Dest={id:string;name:string;lat:number;lng:number;travelMin:number;visitMin:number;returnMin:number;cost:number;
 title:string;intro:string;riddle:string;hints:string[];answers:string[];story:string;activity:string};
export const START={name:"Kozhikode Railway Station",lat:11.2476,lng:75.7836};
export const DESTS:Dest[]=[
{id:"mananchira",name:"Mananchira Square",lat:11.2588,lng:75.7804,travelMin:20,visitMin:30,returnMin:20,cost:40,
 title:"The Quiet Centre",intro:"The case begins where the city goes still.",
 riddle:"A park wraps around still water in the middle of a busy city. Locals gather on its lawns, and the square is named for the water itself, not for any person. Where do you stand?",
 hints:["Think of a public square with a large tank (pond) at its heart.","The name starts with 'Mana' and ends in 'chira'."],
 answers:["mananchira","mananchira square","mananchira maidan","mananchira veedan maidan"],
 story:"Mananchira Square is a public park built around a large tank in the heart of Kozhikode. It is a favourite spot for walks and gatherings.",
 activity:"Walk once around the tank and note what people are doing on the lawns."},
{id:"smstreet",name:"SM Street (Mittai Theruvu)",lat:11.2575,lng:75.7810,travelMin:10,visitMin:30,returnMin:15,cost:120,
 title:"The Sweet Trail",intro:"The next lead is something you can smell before you see it.",
 riddle:"A crowded lane takes its popular name from sugar. Shops here are known for a sticky, ghee-rich sweet sold by weight. Name the street.",
 hints:["Its nickname in Malayalam means 'sweet street'.","SM stands for 'Sweetmeat'."],
 answers:["sm street","s m street","mittai theruvu","mithai theruvu","sweet meat street","sweetmeat street","mittayi theruvu"],
 story:"SM Street, officially Sweet Meat Street and widely called Mittai Theruvu, is a busy shopping lane in central Kozhikode known for its sweets, especially halwa.",
 activity:"Buy a small portion of halwa to share. Prices vary by shop, so ask before buying."},
{id:"beach",name:"Kozhikode Beach",lat:11.2623,lng:75.7670,travelMin:20,visitMin:40,returnMin:30,cost:50,
 title:"Where the City Meets the Sea",intro:"Final chapter. Follow the sound of the waves.",
 riddle:"The Arabian Sea ends this case. Old piers once reached out from this shore, and people come here as the sun drops. Where does the trail end?",
 hints:["Look west. The city's main public shoreline.","Remains of old piers stand in its waters."],
 answers:["kozhikode beach","calicut beach","beach","kozhikode beach front","calicut beach front"],
 story:"Kozhikode Beach is the city's main public shoreline on the Arabian Sea, popular in the evenings. Remains of old piers stand offshore.",
 activity:"Watch the water from the shore. Stay on the open sand, away from the waterline when it is rough."}
];
