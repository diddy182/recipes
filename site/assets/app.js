const search = document.getElementById('search');
const grid = document.getElementById('grid');
const cards = Array.from(grid.querySelectorAll('.card'));
const catChips = Array.from(document.querySelectorAll('.chip[data-cat]'));
const personChips = Array.from(document.querySelectorAll('.chip[data-person]'));
const empty = document.getElementById('empty');
const recent = document.getElementById('recent');
const allTitle = document.getElementById('all-title');
let activeCat = 'all';
let activePerson = 'all';

function apply(){
  const q = search.value.trim().toLowerCase();
  let shown = 0;
  cards.forEach(card => {
    const matchText = !q || card.dataset.search.includes(q);
    const matchCat = activeCat === 'all' || card.dataset.category === activeCat;
    const matchPerson = activePerson === 'all' || card.dataset.contributor === activePerson;
    const show = matchText && matchCat && matchPerson;
    card.style.display = show ? '' : 'none';
    if (show) shown++;
  });
  empty.hidden = shown !== 0;
  // The "Recently Added" strip and "All Recipes" heading are browse-only —
  // hide them once the user starts searching or filtering.
  const browsing = !q && activeCat === 'all' && activePerson === 'all';
  if (recent) recent.style.display = browsing ? '' : 'none';
  if (allTitle) allTitle.style.display = browsing ? '' : 'none';
}

search.addEventListener('input', apply);
catChips.forEach(chip => chip.addEventListener('click', () => {
  catChips.forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activeCat = chip.dataset.cat;
  apply();
}));
personChips.forEach(chip => chip.addEventListener('click', () => {
  personChips.forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activePerson = chip.dataset.person;
  apply();
}));
