# Copyright 2020 The SQLFlow Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
import json
import re
import sys

import six
import sqlflow_models
import tensorflow as tf
import xgboost
from tensorflow.estimator import (BoostedTreesClassifier,
                                  BoostedTreesRegressor, DNNClassifier,
                                  DNNLinearCombinedClassifier,
                                  DNNLinearCombinedRegressor, DNNRegressor,
                                  LinearClassifier, LinearRegressor)


def parse_ctor_args(f, prefix=''):
    """Given an class or function, parse the class constructor/function details
    from its docstring

    For example, the docstring of sqlflow_models.DNNClassifier.__init__ is:
    '''DNNClassifier
    :param feature_columns: feature columns.
    :type feature_columns: list[tf.feature_column].
    :param hidden_units: number of hidden units.
    :type hidden_units: list[int].
    :param n_classes: List of hidden units per layer.
    :type n_classes: int.
    '''
    Calling parse_ctor_args(sqlflow_models.DNNClassifier, ":param") returns:
    {
        "feature_columns": "feature columns. :type feature_columns: list[tf.feature_column].",
        "hidden_units": "number of hidden units. :type hidden_units: list[int].",
        "n_classes": "List of hidden units per layer. :type n_classes: int."
    }
    And calling parse_ctor_args(parse_ctor_args) returns:
    {
        "f": "The class or function whose docstring to parse",
        "prefix": "The prefix of parameters in the docstring"
    }

    Args:
      f: The class or function whose docstring to parse
      prefix: The prefix of parameters in the docstring

    Returns:
      A dict with parameters as keys and splitted docstring as values
    """

    try:
        doc = f.__init__.__doc__
    except:
        doc = ''
    doc = doc if doc else f.__doc__
    if doc is None:
        doc = ''
    arg_list = list(inspect.signature(f).parameters)
    args = '|'.join(arg_list)
    arg_re = re.compile(r'(?<=\n)\s*%s\s*(%s)\s*:\s*' % (prefix, args),
                        re.MULTILINE)
    total = arg_re.split(six.ensure_str(doc))
    # Trim *args and **kwargs if any:
    total[-1] = re.sub(r'(?<=\n)\s*[\\*]+kwargs\s*:.*', '', total[-1], 1,
                       re.M | re.S)

    return dict(
        zip(total[1::2],
            [' '.join(doc.split()).replace("`", "'") for doc in total[2::2]]))


def print_param_doc(*modules):
    param_doc = {}  # { "class_names": {"parameters": "splitted docstrings"} }
    for module in modules:
        models = filter(lambda m: inspect.isclass(m[1]),
                        inspect.getmembers(__import__(module)))
        for name, cls in models:
            param_doc['{}.{}'.format(module,
                                     name)] = parse_ctor_args(cls, ':param')
    print(json.dumps(param_doc))


if __name__ == "__main__":
    param_doc = {}  # { "class_names": {"parameters": "splitted docstrings"} }

    # TensorFlow premade Estimators
    tf_estimators = [
        "DNNClassifier",
        "DNNRegressor",
        "LinearClassifier",
        "LinearRegressor",
        "BoostedTreesClassifier",
        "BoostedTreesRegressor",
        "DNNLinearCombinedClassifier",
        "DNNLinearCombinedRegressor",
    ]
    for cls in tf_estimators:
        param_doc[cls] = parse_ctor_args(eval(cls))

    # xgboost models:  gbtree, gblinear or dart
    param_doc['xgboost.gbtree'] = parse_ctor_args(xgboost.XGBModel)
    del param_doc['xgboost.gbtree'][
        'booster']  # booster specified as an estimator
    param_doc['xgboost.gblinear'] = param_doc['xgboost.gbtree']
    param_doc['xgboost.dart'] = param_doc['xgboost.gbtree']

    print(
        '// Code generated by python symbol_extractor.py > model_parameters.go. DO NOT EDIT.'
    )
    print()
    print('package attribute')
    print()
    print('const ModelParameterJSON = `')
    print(json.dumps(param_doc, indent=4))
    print('`')

    # TensorFlow optimizers
    tf_optimizers = [
        "Adadelta",
        "Adagrad",
        "Adam",
        "Adamax",
        "Ftrl",
        "Nadam",
        "RMSprop",
        "SGD",
    ]
    param_doc.clear()
    for cls in tf_optimizers:
        param_doc[cls] = parse_ctor_args(eval('tf.optimizers.{}'.format(cls)))

    print()
    print('const OptimizerParameterJSON = `')
    print(json.dumps(param_doc, indent=4))
    print('`')