import pytest
import pandas as pd
from io import StringIO
import os
import tempfile

import hierarchical_description03 as hd


@pytest.fixture
def sample_data():
    sample_csv = StringIO(
        """Page,TopLeft_X,TopLeft_Y,Commodity Description,Commodity Number
1,10,100,Cattle:,0010600
1,50,110,Weighing less than 200 pounds each (calves).,0010600
1,70,115,Weighing 200 pounds and less than 700 pounds each.,0010700
1,10,200,Sheep and lambs,0020000
1,50,210,Goats,0021200
1,70,215,Hogs,0021300
1,10,300,Poultry,0014000
1,50,310,Turkeys,0014000
1,70,315,Chickens,0015000
"""
    )
    return pd.read_csv(sample_csv)


def test_combine_split_lines(sample_data):
    combined = hd.combine_split_lines(sample_data, y_threshold=20)
    assert len(combined) <= len(sample_data)
    combined_descs = combined['Commodity Description'].tolist()
    assert any('Weighing less than 200 pounds' in desc for desc in combined_descs)


def test_apply_advanced_ocr_corrections():
    corrected = hd.apply_advanced_ocr_corrections('Catt1e weighing p0unds')
    assert 'Cattle' in corrected
    assert 'pounds' in corrected


def test_is_noise_text():
    assert hd.is_noise_text('SCHEDULE A')
    assert not hd.is_noise_text('Cattle:')


def test_process_commodity_descriptions_by_pixels(sample_data):
    processed = hd.process_commodity_descriptions_by_pixels(sample_data)
    parents = processed[processed['Commodity Description'].str.contains(':')]
    assert all(parents['Commodity Description'].str.endswith(':'))


def test_save_outputs_creates_files(sample_data):
    with tempfile.TemporaryDirectory() as tmpdir:
        final_table_path = os.path.join(tmpdir, "final_table.csv")
        txt_path = os.path.join(tmpdir, "output.txt")
        dummy_final_table = pd.DataFrame({
            'SCHEDULE A COMMODITY NUMBER': ['10600.0', '10700.0'],
            'COMMODITY DESCRIPTION AND ECONOMIC CLASS': ['', '']
        })
        dummy_final_table.to_csv(final_table_path, index=False)

        # Save sample_data to the expected input CSV path for the module
        sample_data.to_csv(hd.INPUT_CSV, index=False)

        try:
            hd.save_outputs(sample_data, final_table_path, txt_path)
        except Exception as e:
            pytest.fail(f"save_outputs raised an exception: {e}")


def test_print_sample(sample_data):
    try:
        hd.print_sample(sample_data, n=3)
    except Exception as e:
        pytest.fail(f"print_sample raised an exception: {e}")