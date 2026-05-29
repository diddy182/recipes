const search = document.getElementById('search');
const grid = document.getElementById('grid');
const cards = Array.from(grid.querySelectorAll('.card'));
const chips = Array.from(document.querySelectorAll('.chip'));
const empty = document.getElementById('empty');
let activeCat = 'all';

function apply(){
  const q = search.value.trim().toLowerCase();
  let shown = 0;
  cards.forEach(card => {
    const matchText = !q || card.dataset.search.includes(q);
    const matchCat = activeCat === 'all' || card.dataset.category === activeCat;
    const show = matchText && matchCat;
    card.style.display = show ? '' : 'none';
    if (show) shown++;
  });
  empty.hidden = shown !== 0;
}

search.addEventListener('input', apply);
chips.forEach(chip => chip.addEventListener('click', () => {
  chips.forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activeCat = chip.dataset.cat;
  apply();
}));
