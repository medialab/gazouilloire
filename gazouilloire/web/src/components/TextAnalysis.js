import React from 'react';
import PropTypes from 'prop-types';

import classNames from 'classnames';
import {withStyles} from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';
import TextField from '@material-ui/core/TextField';
import CircularProgress from '@material-ui/core/CircularProgress';

import Typography from '@material-ui/core/Typography';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import Icon from '@material-ui/core/Icon';

const styles = theme => ({
  progress: {
    margin: theme.spacing.unit * 2
  },
  root: {
    ...theme.mixins.gutters(),
    paddingTop: theme.spacing.unit * 2,
    paddingBottom: theme.spacing.unit * 2
  }
});

const initialState = {
  data: [],
  query: ''
};

class UnstyledTextAnalysis extends React.Component {
  constructor(props) {
    super(props);
    this.state = initialState;
    this._getData = this._getData.bind(this);
  }

  componentDidMount() {
    //this._getData();
  }

  handleSubmit = e => {
    e.preventDefault();
    this._getData('query_string=' + this.state.query);
  };

  handleChange = name => event => {
    this.setState({
      [name]: event.target.value
    });
  };

  _getData(query) {
    this.setState({
      fetchingData: true
    });
    fetch('http://127.0.0.1:5000/textanalysis?' + query)
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
        this.setState({
          data: data,
          fetchingData: false
        });
      });
  }
  render() {
    console.log(this.state);
    const {classes} = this.props;

    var significant_terms = this.state.data.map(function(term) {
      return (
        <ListItem key={term.key}>
          <Icon
            style={{fontSize: 18}}
            className={classNames(classes.icon, 'fas fa-angle-right')}
            color="primary"
          />
          <ListItemText
            primary={term.key}
            secondary={
              'Score: ' + Math.floor(term.score) + ' - Count: ' + term.doc_count
            }
          />
        </ListItem>
      );
    });

    if (this.state.fetchingData) {
      return (
        <Grid container justify="center" alignItems="center">
          <Grid item>
            <CircularProgress className={this.props.classes.progress} />
          </Grid>
        </Grid>
      );
    }

    return (
      <Grid
        container
        style={{width: '100%', height: '100%'}}
        direction="row"
        alignItems="center"
        justify="center"
        spacing={32}
      >
        <Grid
          container
          direction="column"
          alignItems="center"
          justify="center"
          spacing={32}
        >
          <Grid item>
            <Typography
              color="primary"
              variant="button"
              style={{fontWeight: 'bold'}}
              noWrap
            >
              Significant terms
            </Typography>
            <form
              className={classes.container}
              onSubmit={this.handleSubmit}
              noValidate
              autoComplete="off"
            >
              <TextField
                id="outlined-name"
                label="Query"
                className={classes.textField}
                value={this.state.query}
                onChange={this.handleChange('query')}
                margin="normal"
                variant="outlined"
              />
            </form>
          </Grid>
          <Grid item>
            <List
              style={{
                marginTop: '0px',
                width: '60vw',
                maxHeight: '60vh',
                overflow: 'auto'
              }}
              component="nav"
            >
              {significant_terms}
            </List>
          </Grid>
        </Grid>
      </Grid>
    );
  }
}

UnstyledTextAnalysis.propTypes = {
  classes: PropTypes.object.isRequired
};

const TextAnalysis = withStyles(styles)(UnstyledTextAnalysis);

export default TextAnalysis;
