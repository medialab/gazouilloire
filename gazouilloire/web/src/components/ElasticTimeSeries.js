import {
  LineChart,
  Line,
  Label,
  Legend,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceArea,
  ResponsiveContainer
} from 'recharts';
import React from 'react';
import PropTypes from 'prop-types';
import {withStyles} from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import Button from '@material-ui/core/Button';
import {Typography} from '@material-ui/core';
import Paper from '@material-ui/core/Paper';
import CircularProgress from '@material-ui/core/CircularProgress';
import DatePicker from 'material-ui-pickers/DateTimePicker';
import Icon from '@material-ui/core/Icon';
import classNames from 'classnames';

const styles = theme => ({
  progress: {
    margin: theme.spacing.unit * 2
  }
});

//Zoom-linked functions & variables

const initialState = {
  data: null,
  startDate: null,
  endDate: null,
  left: 'dataMin',
  right: 'dataMax',
  refAreaLeft: '',
  refAreaRight: '',
  top: 'dataMax + (dataMax-dataMin)*0.05',
  bottom: 'dataMin - (dataMax-dataMin)*0.05',
  animation: true
};

var dateFormat = 'dash';

function toTimestamp(x) {
  if (typeof x == 'string') {
    var d = new Date(x);
    d.setHours(d.getHours() + 1);
    return d.getTime() / 1000;
  }
  if (typeof x == 'object') return x.getTime() / 1000;
}

function stringToDate(string, format = dateFormat) {
  if (format == 'dash') {
    var date = new Date(string);
  } else if (format == 'nothing') {
    var date = new Date(
      string.slice(0, 4),
      Number(string.slice(4, 6)) - 1,
      string.slice(6, 8)
    );
  }
  return date;
}

function formatXAxis(tickItem) {
  var date = new Date(tickItem * 1000);
  var year = date.getFullYear();
  var month = date.getMonth() + 1;
  var day = date.getDate();
  return day + '/' + month + '/' + year;
}

class UnstyledTimeSeries extends React.Component {
  constructor(props) {
    super(props);
    this.state = initialState;
    this.zoom = this.zoom.bind(this);
    this.zoomOut = this.zoomOut.bind(this);
    this.getAxisYDomain = this.getAxisYDomain.bind(this);
    this.dateToXIndex = this.dateToXIndex.bind(this);
  }

  //Zoom-linked functions
  dateToXIndex(date) {
    const data = this.state.data;
    var oneDay = 24 * 60 * 60 * 1000;
    var debut_date = new Date(data[0]['_id']);
    date = new Date(date);
    var index = Math.round(
      Math.abs((date.getTime() - debut_date.getTime()) / oneDay)
    );
    return index;
  }

  getAxisYDomain(from, to, ref, offset) {
    console.log('From = ', from, ' & To = ', to);
    const {data, completeData} = this.state;

    //DATE RANGE TO INT RANGE CONVERSION ---

    var oneDay = 24 * 60 * 60 * 1000; // hours*minutes*seconds*milliseconds
    var oneHour = 60 * 60 * 1000;
    var debut_date = new Date(data[0]['_id']);
    var from_date = new Date(from);
    var to_date = new Date(to);
    var diffDays = Math.round(
      Math.abs((to_date.getTime() - from_date.getTime()) / oneDay)
    );
    var xfrom = Math.round(
      Math.abs((from_date.getTime() - debut_date.getTime()) / oneDay)
    );
    this.state.refAreaLeftNumber = xfrom;
    var xto = Math.round(
      Math.abs((to_date.getTime() - debut_date.getTime()) / oneDay)
    );
    this.state.refAreaRightNumber = xto;
    console.log('xfrom = ', xfrom, 'xto = ', xto);

    // --- DATE RANGE TO INT RANGE CONVERSION

    for (var i = 0; i < completeData.length; i++) {
      if (completeData[i]['_id'] == from) var fromIndex = i;
      if (completeData[i]['_id'] == to) var toIndex = i;
    }
    const refData = completeData.slice(fromIndex - 1, toIndex + 1);
    console.log('Refdata = ', refData);
    console.log('Ref = ', ref);
    let [bottom, top] = [refData[0][ref], refData[0][ref]];
    refData.forEach(d => {
      if (d[ref] > top) top = d[ref];
      if (d[ref] < bottom) bottom = d[ref];
    });
    this.state.yMax = top;
    this.state.yMin = bottom;
    offset = Math.round((top - bottom) * 0.05);
    return [(bottom | 0) - offset, (top | 0) + offset];
  }

  zoom() {
    console.log('ZOOM ---------');
    let data = this.state.data;
    let {refAreaLeft, refAreaRight, left, right} = this.state;

    if (refAreaLeft === refAreaRight || refAreaRight === '') {
      this.setState(() => ({
        refAreaLeft: '',
        refAreaRight: ''
      }));
      return;
    }

    // yAxis domain
    const [bottom, top] = this.getAxisYDomain(
      refAreaLeft,
      refAreaRight,
      'count'
    );

    let {refAreaLeftNumber, refAreaRightNumber} = this.state;

    // xAxis domain
    if (refAreaLeft > refAreaRight)
      [refAreaLeft, refAreaRight] = [refAreaRight, refAreaLeft];

    console.log(
      'bottom : ',
      bottom,
      ', top : ',
      top,
      ', refAreaLeftNumber : ',
      refAreaLeftNumber,
      ', refAreaRightNumber : ',
      refAreaRightNumber,
      ', refAreaLeft : ',
      refAreaLeft,
      ', refAreaRight : ',
      refAreaRight
    );

    this.setState(() => ({
      left: refAreaLeft,
      right: refAreaRight,
      refAreaLeft: '',
      refAreaRight: '',
      data: data.slice(),
      bottom,
      top
    }));
    console.log('--------- ZOOM');
  }

  zoomOut() {
    console.log('ZoomOut');
    const {data} = this.state;
    this.setState(() => ({
      data: data.slice(),
      refAreaLeft: '',
      refAreaRight: '',
      refAreaLeftNumber: '',
      refAreaRightNumber: '',
      left: 'dataMin',
      right: 'dataMax',
      top: 'dataMax+1',
      bottom: 'dataMin'
    }));
  }

  //Data-linked functions

  componentDidMount() {
    console.log('componentDidMount');
    this._getData();
  }

  _getData() {
    console.log('_getData');
    fetch(
      'http://127.0.0.1:5000/elastictimeevolution?index=' +
        this.props.index +
        '_tweets'
    )
      .then(response => {
        if (response.ok) {
          console.log('Flask server response ok', response);
          return response;
        } else {
          console.log('Flask server response not ok', response);
          let errorMessage = '${response.status(${response.statusText})',
            error = new Error(errorMessage);
          throw error;
        }
      })
      .then(response => response.json())
      .then(json => {
        const data = json;
        if (
          (stringToDate(data[1]['_source']['timestamp']) -
            stringToDate(data[0]['_source']['timestamp'])) /
            (1000 * 60 * 60 * 24) >
          300
        ) {
          console.log(
            'Removing first element in data : element chronologically too far from others'
          );
          data.shift();
        }
        var startDate = stringToDate(data[0]['_source']['timestamp']);
        console.log('startDate : ', startDate);
        var endDate = stringToDate(
          data[data.length - 1]['_source']['timestamp']
        );
        this.setState({
          data: data,
          startDate: startDate,
          endDate: endDate
        });
        console.log('json', json);
      });

    console.log('Fin _getData');
  }

  render() {
    console.log('data : ', this.state.data);
    console.log('this.state.startDate : ', this.state.startDate);
    var data = this.state.data;
    const {classes} = this.props;

    if (!this.state.data) {
      return <CircularProgress className={this.props.classes.progress} />;
    }
    {
      /* Filling the no-records days with a 0 count to have a complete data range*/
    }

    var startDate = stringToDate(data[0]['_source']['timestamp']);
    console.log('startDate : ', startDate);
    var endDate = stringToDate(data[data.length - 1]['_source']['timestamp']);

    if (!this.state.startDate) {
      this.setDateRange(startDate, endDate);
    }

    var completeData = [];
    for (var d = startDate; d <= endDate; d.setDate(d.getDate() + 1)) {
      var nbTweets = 0;
      for (var j = 0; j < data.length; j++) {
        if (toTimestamp(data[j]['_source']['timestamp']) === toTimestamp(d)) {
          nbTweets = data[j]['count'];
          continue;
        }
        //console.log('Day Count = 0 : ', toTimestamp(data[j]['_id']), ' =/= ', toTimestamp(d));
      }
      var day = {_id: toTimestamp(d), count: nbTweets};
      //if (toTimestamp(d) > 1536584993) console.log('Day Count : ', nbTweets, ', date : ', d);
      completeData.push(day);
    }

    this.state.completeData = completeData;
    console.log('completeData: ', completeData);

    const {
      barIndex,
      completeData,
      left,
      right,
      refAreaLeft,
      refAreaRight,
      refAreaLeftNumber,
      refAreaRightNumber,
      top,
      bottom
    } = this.state;
    {
      /*console.log(
      'left : ',
      left,
      ', right : ',
      right,
      ', refAreaLeft : ',
      refAreaLeft,
      ', refAreaRight : ',
      refAreaRight,
      ', refAreaLeftNumber : ',
      refAreaLeftNumber,
      ', refAreaRightNumber : ',
      refAreaRightNumber
    );*/
    }
    return (
      <Grid
        container
        justify="center"
        alignItems="center"
        direction="column"
        spacing={32}
      >
        <Grid
          container
          justify="center"
          alignItems="center"
          direction="row"
          spacing={16}
        >
          <Grid item>
            <Button onClick={this.zoomOut.bind(this)}>
              <Icon
                style={{marginRight: '8px', fontSize: 18}}
                className={classNames(classes.icon, 'fas fa-compress')}
              />
              Zoom Out{' '}
            </Button>
          </Grid>
        </Grid>
        <Grid
          item
          style={{
            width: '90vw',
            maxWidth: '90vw',
            height: '80vh',
            maxHeight: '80vh'
          }}
        >
          <ResponsiveContainer>
            <LineChart
              data={completeData}
              margin={{top: 20, right: 20, bottom: 20, left: 0}}
              onMouseDown={e =>
                this.setState({
                  refAreaLeft: e.activeLabel
                })
              }
              onMouseMove={e =>
                this.state.refAreaLeft &&
                this.setState({
                  refAreaRight: e.activeLabel
                })
              }
              onMouseUp={this.zoom.bind(this)}
              style={{fontFamily: 'Raleway'}}
            >
              <Line
                yAxisId="1"
                name="Nb of tweets / day"
                type="monotone"
                dataKey="count"
                stroke="#247ba0"
                animationDuration={300}
              />
              <CartesianGrid
                stroke="#ccc"
                strokeDasharray="5 5"
                style={{marginBottom: '20px'}}
              />
              <XAxis
                allowDataOverflow={true}
                dataKey="_id"
                type="number"
                name="Day"
                tickFormatter={formatXAxis}
                tick={{fontFamily: 'Raleway'}}
                domain={[left, right]}
                style={{marginTop: '10px'}}
                interval="preserveStartEnd"
              />
              <YAxis
                allowDataOverflow={true}
                domain={[
                  Math.round(bottom - (top - bottom) * 0.1),
                  Math.round(top + (top - bottom) * 0.1)
                ]}
                type="number"
                yAxisId="1"
                dataKey="count"
                name="Nb of tweets"
                padding={{bottom: 10}}
              />
              <Tooltip labelFormatter={formatXAxis} />
              {refAreaLeft && refAreaRight ? (
                <ReferenceArea
                  yAxisId="1"
                  x1={refAreaLeft}
                  x2={refAreaRight}
                  strokeOpacity={0.3}
                />
              ) : null}
              <Legend style={{fontFamily: 'Raleway'}} />
            </LineChart>
          </ResponsiveContainer>
        </Grid>
      </Grid>
    );
  }
}

UnstyledTimeSeries.propTypes = {
  classes: PropTypes.object.isRequired
};

const TimeSeries = withStyles(styles)(UnstyledTimeSeries);

export default TimeSeries;
