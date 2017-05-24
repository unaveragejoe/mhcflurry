# Copyright (c) 2016. Mount Sinai School of Medicine
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tempfile
import shutil

import pandas
from mhcflurry.downloads import get_path
from mhcflurry import Class1AffinityPredictor

DOWNLOADED_PREDICTOR = Class1AffinityPredictor.load()


def predict_and_check(
        allele,
        peptide,
        predictor=DOWNLOADED_PREDICTOR,
        expected_range=(0, 500)):

    def debug():
        print("\n%s" % (
            predictor.predict_to_dataframe(
                peptides=[peptide],
                allele=allele,
                include_individual_model_predictions=True)))

        (prediction,) = predictor.predict(allele=allele, peptides=[peptide])
        assert prediction >= expected_range[0], (predictor, prediction, debug())
        assert prediction <= expected_range[1], (predictor, prediction, debug())


def test_A1_Titin_epitope_downloaded_models():
    # Test the A1 Titin epitope ESDPIVAQY from
    #   Identification of a Titin-Derived HLA-A1-Presented Peptide
    #   as a Cross-Reactive Target for Engineered MAGE A3-Directed
    #   T Cells
    predict_and_check("HLA-A*01:01", "ESDPIVAQY")


def test_A1_MAGE_epitope_downloaded_models():
    # Test the A1 MAGE epitope EVDPIGHLY from
    #   Identification of a Titin-Derived HLA-A1-Presented Peptide
    #   as a Cross-Reactive Target for Engineered MAGE A3-Directed
    #   T Cells
    predict_and_check("HLA-A*01:01", "EVDPIGHLY")


def test_A2_HIV_epitope_downloaded_models():
    # Test the A2 HIV epitope SLYNTVATL from
    #    The HIV-1 HLA-A2-SLYNTVATL Is a Help-Independent CTL Epitope
    predict_and_check("HLA-A*02:01", "SLYNTVATL")


def test_A1_trained_models():
    allele = "HLA-A*01:01"
    df = pandas.read_csv(
        get_path(
            "data_curated", "curated_training_data.csv.bz2"))
    df = df.ix[
        (df.allele == allele) &
        (df.peptide.str.len() >= 8) &
        (df.peptide.str.len() <= 15)
    ]

    hyperparameters = {
        "max_epochs": 500,
        "patience": 10,
        "early_stopping": True,
        "validation_split": 0.2,

        "random_negative_rate": 0.0,
        "random_negative_constant": 25,

        "use_embedding": False,
        "kmer_size": 15,
        "batch_normalization": False,
        "locally_connected_layers": [
            {
                "filters": 8,
                "activation": "tanh",
                "kernel_size": 3
            },
            {
                "filters": 8,
                "activation": "tanh",
                "kernel_size": 3
            }
        ],
        "activation": "relu",
        "output_activation": "sigmoid",
        "layer_sizes": [
            32
        ],
        "random_negative_affinity_min": 20000.0,
        "random_negative_affinity_max": 50000.0,
        "dense_layer_l1_regularization": 0.001,
        "dropout_probability": 0.0
    }

    predictor = Class1AffinityPredictor()
    predictor.fit_allele_specific_predictors(
        n_models=2,
        architecture_hyperparameters=hyperparameters,
        allele=allele,
        peptides=df.peptide.values,
        affinities=df.measurement_value.values,
    )

    predict_and_check("HLA-A*01:01", "EVDPIGHLY", predictors=[predictor])

    models_dir = tempfile.mkdtemp("_models")
    print(models_dir)
    predictor.save(models_dir)
    predictor2 = Class1AffinityPredictor.load(models_dir)
    predict_and_check("HLA-A*01:01", "EVDPIGHLY", predictors=[predictor2])
    shutil.rmtree(models_dir)

    predictor3 = Class1AffinityPredictor(
        allele_to_allele_specific_models={
            allele: [predictor.allele_to_allele_specific_models[allele][0]]
        })
    predict_and_check("HLA-A*01:01", "EVDPIGHLY", predictors=[predictor3])
    models_dir = tempfile.mkdtemp("_models")
    print(models_dir)
    predictor3.save(models_dir)
    predictor4 = Class1AffinityPredictor.load(models_dir)
    predict_and_check("HLA-A*01:01", "EVDPIGHLY", predictors=[predictor4])
    shutil.rmtree(models_dir)

