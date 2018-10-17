import React, {Component} from 'react';
import PropTypes from 'prop-types';
import classNames from 'classnames';
import {withStyles} from '@material-ui/core/styles';
import ChipInput from 'material-ui-chip-input';
import Grid from '@material-ui/core/Grid';
import TextField from '@material-ui/core/TextField';
import Typography from '@material-ui/core/Typography';
import Icon from '@material-ui/core/Icon';
import Button from '@material-ui/core/Button';
// Switch
import Switch from '@material-ui/core/Switch';
import FormControlLabel from '@material-ui/core/FormControlLabel';

const styles = theme => ({
  root: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'flex-end'
  },
  icon: {
    'margin-right': theme.spacing.unit * 2
  },
  iconHover: {
    margin: theme.spacing.unit * 2,
    '&:hover': {
      color: theme.palette.secondary
    }
  },
  chip: {
    'background-color': 'primary'
  },
  container: {
    display: 'flex',
    flexWrap: 'wrap'
  },
  textField: {
    marginLeft: theme.spacing.unit,
    marginRight: theme.spacing.unit
  },
  dense: {
    marginTop: 16
  },
  menu: {
    width: 200
  }
});

class Parameters extends Component {
  constructor(props) {
    super(props);
    this.state = {
      fromDate: new Date(),
      toDate: new Date(),
      keywords: [],
      urls: [],
      includeThreads: false,
      consumerKey: '',
      consumerSecret: '',
      accessToken: '',
      accessTokenSecret: ''
    };
    this.handleFromDateChange = this.handleFromDateChange.bind(this);
    this.handleToDateChange = this.handleToDateChange.bind(this);
    this.handleDeleteKeyword = this.handleDeleteKeyword.bind(this);
    this.handleAddKeyword = this.handleAddKeyword.bind(this);
    this.handleDeleteURL = this.handleDeleteURL.bind(this);
    this.handleAddURL = this.handleAddURL.bind(this);
    this.handleIncludeThreadsChange = this.handleIncludeThreadsChange.bind(
      this
    );
  }

  handleChange = name => event => {
    this.setState({
      [name]: event.target.value
    });
  };

  handleFromDateChange(date) {
    this.setState({
      fromDate: date
    });
  }

  handleToDateChange(date) {
    this.setState({
      toDate: date
    });
  }

  handleDeleteKeyword(chip, index) {
    this.setState({
      keywords: this.state.keywords.filter((_, i) => i !== index)
    });
  }

  handleAddKeyword(data) {
    this.setState(state => ({
      keywords: [...state.keywords, data]
    }));
  }

  handleDeleteURL(chip, index) {
    this.setState({
      urls: this.state.urls.filter((_, i) => i !== index)
    });
  }

  handleAddURL(data) {
    this.setState(state => ({
      urls: [...state.urls, data]
    }));
  }

  handleIncludeThreadsChange() {
    this.setState(state => ({includeThreads: !state.includeThreads}));
  }

  render() {
    const {classes} = this.props;
    console.log(this.state.accessTokenSecret);

    return (
      <Grid
        container
        style={{width: '100%', height: '100%'}}
        direction="row"
        alignItems="center"
        justify="center"
        spacing={32}
      >
        <Grid item xs={6} style={{marginRight: '0px'}}>
          <Grid
            container
            style={{width: '100%'}}
            direction="column"
            justify="center"
            alignItems="center"
            spacing={8}
          >
            <Grid
              style={{marginTop: '0px', marginBottom: '0px'}}
              container
              direction="row"
              alignItems="center"
              justify="center"
            >
              <Grid item>
                <Icon
                  style={{fontSize: 18}}
                  className={classNames(classes.icon, 'fas fa-key')}
                  color="primary"
                />
              </Grid>
              <Grid item>
                <Typography
                  color="primary"
                  variant="button"
                  style={{fontWeight: 'bold'}}
                  noWrap
                >
                  API Keys Parameters
                </Typography>
              </Grid>
            </Grid>
            <Grid item>
              <form className={classes.container} noValidate autoComplete="off">
                <TextField
                  id="outlined-name"
                  label="Consumer API Key"
                  className={classes.textField}
                  value={this.state.consumerKey}
                  onChange={this.handleChange('consumerKey')}
                  margin="normal"
                  variant="outlined"
                />
              </form>
            </Grid>
            <Grid item>
              <form className={classes.container} noValidate autoComplete="off">
                <TextField
                  id="outlined-name"
                  label="Consumer API Secret"
                  className={classes.textField}
                  value={this.state.consumerSecret}
                  onChange={this.handleChange('consumerSecret')}
                  margin="normal"
                  variant="outlined"
                />
              </form>
            </Grid>
            <Grid item>
              <form className={classes.container} noValidate autoComplete="off">
                <TextField
                  id="outlined-name"
                  label="Access Token"
                  className={classes.textField}
                  value={this.state.accessToken}
                  onChange={this.handleChange('accessToken')}
                  margin="normal"
                  variant="outlined"
                />
              </form>
            </Grid>
            <Grid item>
              <form className={classes.container} noValidate autoComplete="off">
                <TextField
                  id="outlined-name"
                  label="Access Token Secret"
                  className={classes.textField}
                  value={this.state.accessTokenSecret}
                  onChange={this.handleChange('accessTokenSecret')}
                  margin="normal"
                  variant="outlined"
                />
              </form>
            </Grid>
          </Grid>
        </Grid>
        <Grid item xs={6} style={{marginLeft: '0px'}}>
          <Grid
            container
            style={{margin: 0, width: '100%'}}
            direction="column"
            justify="center"
            alignItems="center"
            spacing={32}
          >
            <Grid
              style={{marginTop: '0px', marginBottom: '10px'}}
              container
              direction="row"
              alignItems="center"
              justify="center"
            >
              <Grid item>
                <Icon
                  style={{fontSize: 18}}
                  className={classNames(classes.icon, 'fas fa-sliders-h')}
                  color="primary"
                />
              </Grid>
              <Grid item>
                <Typography
                  color="primary"
                  variant="button"
                  style={{fontWeight: 'bold'}}
                  noWrap
                >
                  Collect Parameters
                </Typography>
              </Grid>
            </Grid>
            <Grid item style={{marginBottom: '10px'}}>
              <Typography variant="body2" noWrap>
                Keywords
              </Typography>
              <ChipInput
                style={{width: '350px'}}
                value={this.state.keywords}
                fullWidth={false}
                fullWidthInput={false}
                placeholder="Type & press Enter"
                helperText="Avoid accents. Add '@' to search for a user."
                onAdd={chip => this.handleAddKeyword(chip)}
                onDelete={(chip, index) =>
                  this.handleDeleteKeyword(chip, index)
                }
                //chipRenderer={({value}, key) => <Chip style={{'color':'primary'}} value={value} key={key} />}
              />
            </Grid>

            <Grid item style={{marginBottom: '10px'}}>
              <Typography variant="body2" noWrap>
                URLs
              </Typography>
              <ChipInput
                style={{width: '350px'}}
                value={this.state.urls}
                fullWidth={false}
                fullWidthInput={false}
                placeholder="Type & press Enter"
                helperText="Example: medialab.sciencespo.fr"
                onAdd={chip => this.handleAddURL(chip)}
                onDelete={(chip, index) => this.handleDeleteURL(chip, index)}
              />
            </Grid>

            {/*<Grid item>
              <Typography variant="body2" noWrap>
                From
              </Typography>
              <DateTimePicker
                value={this.state.fromDate}
                onChange={this.handleFromDateChange}
                disableFuture={true}
              />
            </Grid>

            <Grid item>
              <Typography variant="body2" noWrap>
                To
              </Typography>
              <DateTimePicker
                value={this.state.toDate}
                onChange={this.handleToDateChange}
                disableFuture={true}
              />
            </Grid>*/}

            <Grid item>
              <FormControlLabel
                control={
                  <Switch
                    checked={this.state.includeThreads}
                    onChange={this.handleIncludeThreadsChange}
                    value="includeThreads"
                  />
                }
                label="Include threads"
              />
            </Grid>

            <Grid item>
              <Button
                style={{
                  margin: '0px',
                  background:
                    'linear-gradient(45deg, #247ba0, #4278ac, #6473b0, #876bac,#bb5b89 )',
                  color: 'white'
                }}
                variant="extendedFab"
                aria-label="Delete"
                className={classes.button}
              >
                <Icon
                  style={{marginLeft: '4px', fontSize: 18}}
                  className={classNames(classes.icon, 'fas fa-play')}
                />
                Start Collect
              </Button>
            </Grid>

            {/* Try this : https://www.npmjs.com/package/material-ui-datetime-range-picker */}
          </Grid>
        </Grid>
      </Grid>
    );
  }
}

Parameters.propTypes = {
  classes: PropTypes.object.isRequired
};

const StyledParameters = withStyles(styles)(Parameters);

export default StyledParameters;
