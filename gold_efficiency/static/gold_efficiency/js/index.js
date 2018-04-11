var qsRegex;

var $box = $('.box-container').isotope({
  itemSelector:'.box',
  getSortData: {
    name: '.item-name',
    efficiency: function (elem) {
      let eff = parseFloat($(elem).find('.efficiency').text().replace('%', ''));
      return eff;
    },
    value: function (elem) {
      let str = $(elem).find('.value').text().match(/\d+\.*\d*G/)[0];
      return parseFloat(str.replace('G', ''));
    },
    cost: function (elem) {
      let str = $(elem).find('.total').text().match(/\d*G/)[0];
      return parseInt(str.replace('G', ''));
    },
    tier: function (elem) {
      let tier = $(elem).find('.tier').text().replace('Tier: ','');
      console.log(tier)
      return parseInt(tier);
    },
  },
  filter: function() {
    return qsRegex ? $(this).text().match( qsRegex ) : true;
  },
  masonry: {
    columnWidth: 100
  }
});

$('.btn-group').on('click', 'button', function(){
  var sortValue = $(this).attr('sort-type');
  console.log(sortValue);
  $box.isotope({
    sortBy: sortValue,
    sortAscending: false,
  });
});

// use value of search field to filter
var $quicksearch = $('.quicksearch').keyup( debounce( function() {
  qsRegex = new RegExp( $quicksearch.val(), 'gi' );
  $box.isotope();
}, 200 ) );

// debounce so filtering doesn't happen every millisecond
function debounce( fn, threshold ) {
  var timeout;
  threshold = threshold || 100;
  return function debounced() {
    clearTimeout( timeout );
    var args = arguments;
    var _this = this;
    function delayed() {
      fn.apply( _this, args );
    }
    timeout = setTimeout( delayed, threshold );
  };
}
