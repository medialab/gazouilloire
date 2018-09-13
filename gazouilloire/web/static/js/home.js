(function(ns){
  ns.addDatePicker = function(id){
    $('#'+id).datepicker({format: 'yyyy-mm-dd'})
    .on('changeDate', function(e){console.log(e)});
  };
  ns.addTagSelect = function(id, initVals){
    var input = $('#'+id),
      hid = $('input[name='+id+']'),
      getHid = function(){ return hid.val().split(/\|/)},
      formatHid = function(vals){
        hid.val(vals.filter(function(v){ return v }).join('|'));
      };
    input.tagsinput();
    initVals.split(/\|/).forEach(function(val){
      input.tagsinput('add', val);
    });
    $(input).on('itemAdded', function(e){
      var values = getHid();
      values.push(e.item);
      formatHid(values);
    }).on('itemRemoved', function(e){
      formatHid(getHid().filter(function(v){ return v !== e.item }))
    });
  };
  ns.submit = function(){
    var dataUrl = $("form").attr("action") + "?" + $("form").serialize();
    $('#loader').show();
    $('#submit').attr("disabled", "disabled");
    $('#errors').hide();
    $('#errors ul').empty();
    $('#nomatch').hide();
    if (ns.table) {
      $('#preview').hide();
      ns.table.destroy();
      $('#preview table').empty();
    }
    d3.csv(dataUrl, function(d){
      return d;
    }, function(error, data){
      $('#loader').hide();
      $('#submit').attr("disabled", null);
      if (error)
        return console.log(data, error);
      if (data.columns[0] === "error") {
        $('#errors').show();
        return d3.select('#errors ul')
          .selectAll('li')
          .data(data).enter()
          .append('li')
          .text(function(d){ return d.error});
      }
      if (!data.length)
        return $('#nomatch').show();
      $('#preview').show();
      ns.table = $('#preview table').DataTable({
        data: data,
        columns: [
          { data: 'id' },
          { data: 'from_user_name' },
          { data: 'text' },
          { data: 'created_at' }
        ]
      });
    });
  };
  ns.download = function(){
    $('form').submit();
  };

  var parseDate = d3.timeParse("%Y-%m-%d"),
    formatCount = d3.format(",.0f");
    prepareDate = function(d){
      d.count = +d.count;
      d.date = parseDate(d.time);
      return d;
    };

  var margin = {top: 10, right: 30, bottom: 30, left: 30},
    width = $('.well').width() - margin.left - margin.right,
    height = 500 - margin.top - margin.bottom;

  var x = d3.scaleTime()
    .rangeRound([0, width]);

  var y = d3.scaleLinear()
    .range([height, 0]);

  /*var histogram = d3.histogram()
    .value(function(d) { return d.key; })
    .domain(x.domain())
    .thresholds(x.ticks(d3.timeMonth));
*/

  var svg = d3.select(".well").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  $(document).ready(function(){
    ns.addDatePicker('startdate');
    ns.addDatePicker('enddate');
    ns.addTagSelect('query', $('#query_val').val());
    ns.addTagSelect('filters', $('#filters_val').val());
    $('#submit').on('click', ns.submit);
    $('#download').on('click', ns.download);
    $('#threads').on('change', function(d){
      $("#threads_val").val(d.currentTarget.checked ? "checked" : "");
    });
    $('#selected').on('change', function(d){
      $("#selected_val").val(d.currentTarget.checked ? "checked" : "");
    });
    $('.bootstrap-tagsinput').addClass('col-md-8 col-xs-8')
    $('form').on('change', function(){console.log("WOUP")});
    d3.csv('/api/histo', prepareDate, function(error, bins){
      if (error) throw error;
      console.log(bins)

      /*var bins = d3.nest()
        .key(function(d){ return new Date(d3.timeWeek(d.date))})
        .rollup(function(a){ return d3.sum(a, function(d){ return d.count; })})
        .entries(data)
      console.log(bins)
*/
      x.domain([new Date(2016,10,1), d3.max(bins, function(d) { return d.date; })]);
      y.domain([0, d3.max(bins, function(d) { return d.count; })]);

      svg.append("g")
        .attr("class", "axis axis--x")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x));

      svg.append("g")
        .attr("class", "axis axis--y")
        .call(d3.axisLeft(y));
        /*d3.svg.axis()
        .scale(y)
        .orient("left"));*/

      var histo = svg.selectAll(".bar")
        .data(bins)
        .enter().append("g")
        .attr("class", "bar")
        .attr("transform", function(d) { return "translate(" + x(d.date) + "," + y(d.count) + ")"; });
        /*.attr("x", function(d) { return x(d.offset); })
        .attr("width", function(d) { return x(d.width) - 1; })
        .attr("y", function(d) { return y(d.height); })
        .attr("height", function(d) { return height - y(d.height); });
*/

      var barWidth = 0.95*(x(new Date(2015, 0, 8)) - x(new Date(2015, 0, 7)));

      histo.append("rect")
        .attr("x", 1)
        .attr("width", barWidth)
        .attr("height", function(d) { return height - y(d.count); });

      histo.append("text")
        .attr("dy", ".75em")
        .attr("y", 6)
        .attr("x", function(d) { return barWidth / 2; })
        .attr("text-anchor", "middle")
        .text(function(d) { return formatCount(d.count); });

    });
  });
})(window.gazouilloireExportForm = window.gazouilloireExportForm || {});

/*


    Full Smart Netowrk : Do a full representation of User, Tweet, Hashtag, Url, Media & Symbol
    User Network : Do a weighter User to User network with parallel edges for RT and Mentions
    Hashtag Network : A weighted Hashtag to Hashtag network

*/
