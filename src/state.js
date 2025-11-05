export const state = {
  peopleCache: {},       // name -> events[]
  personStyles: {},      // name -> style
  events: [],            // 当前展示的事件
  currentPerson: '毛泽东',
  currentIndex: 0,
  playTimer: null,
  allNames: [],
  filteredNames: [],
  activeSuggestIndex: -1,
  map: null,
  markers: [],
  polyline: null,
};

export function setPersonData(name, events, style) {
  state.currentPerson = name;
  state.peopleCache[name] = events || [];
  if (style) state.personStyles[name] = style;
  state.events = state.peopleCache[name] || [];
  state.currentIndex = 0;
}

export function setCurrentIndex(i) {
  state.currentIndex = i;
}

export function setPlayTimer(timer) {
  state.playTimer = timer;
}