# Aerosol Input Formatter for RRTM Suite
This is a web application with a python backend that takes aerosol optical properties as inputs according to the RRTM(G) instructions for aerosol input files.
> - You can access the Docker-based HuggingFace app directly without cloning or running this repo locally: **https://huggingface.co/spaces/nagakasam/Aerosol-Formatter_for_RRTM**

---

> ## Application for RRTM Suite of Radiative Transfer Models
> The followig repository is a scientific computational application for running radiative transfer simulations: **https://github.com/AER-RC/RRTMG_SW.git**
> 
> Though the above package contains the RRTM radiative transfer model developed at **AER** for application to GCMs, its ability to run as vertical column model enable small scale applications of the software. As such, the addition of new aerosols and their subsequent properties may be burdensome if not familiar with FORTRAN formatting.
> 
> The **rrtmg_sw_instructions.txt** file in the documents folder of the aforementioned package provides instructions for the addition of aerosols as a separate input file under IN_AER_RRTM.
> 
> However, working with aerosol data and formatting it into a file may become cumbersome, especially if dealing with multiple aerosols. Therefore, the *Aerosol Input Formatter* takes individual inputs for all the necessary data required to format the IN_AER_RRTM file. It removes the need for single character validation as FORTRAN necessitates precise formatting. This program prompts for inputs dynamically as certain options are enabled via the dropdowns.

---

## Purpose
RRTM-G (Rapid Radiative Transfer Model - Global) requires aerosol input files with specific formatting and parameter constraints. Manually preparing these files can be error-prone and time-consuming, especially when dealing with multiple aerosol types, layers, and spectral bands.

This tool provides a structured interface for entering aerosol parameters such as:

- Number of aerosol types (NAER)
- Number of layers (NLAY)
- Optical depth mode (IOAD)
- Single-scattering albedo mode (ISSA)
- Asymmetry parameter mode (IPHA)
- Per-band values for extinction, SSA, and asymmetry factor

The formatter validates inputs, dynamically adjusts the form based on user selections, and generates a model-ready `Aer_input.txt` file to the local machine as a downloadable that can be directly placed in the IN_AER_RRTM input file for conducting simulations.

---

## Features

- Dynamic form generation based on NAER and NLAY values
- Support for both gray and spectral band (IB16-29) optical depth modes
- Input validation for RRTM-G parameter ranges
  -  Inputs with invalid arguments will return a comprehensive error report for verification and re-application by the user
- Automatic formatting of output file compatible with AER RRTM-G
  
### Huggingface Web App
- Cloud-hosted interface via HuggingFace
- Gunicorn WSGI used for its pre-fork worker based architecture
- Dockerized deployment for reproducibility and security
- This Dockerized deployment enables the users to run the application alongside its dependencies within the container

---

## Technologies Used

- Python 3.10
- Flask (web framework)
- HTML, CSS, JavaScript (for dynamic form behavior)
- Docker (for containerized deployment)
- Hugging Face Spaces (for cloud hosting)

---

## Local Development

To run app locally, you can employ conda or any other virtual environment with the dependencies listed in **requirements.txt**.

---

## Contributions

Contributions are welcome. Please open an issue or submit a pull request if you’d like to improve the interface, add support for new modes, enhance validation, or improve or add functionality based on various use cases.

---

## License

This project is open-source and intended for research and educational use. Please cite appropriately if used in published work.

---

## Author

Developed by Naga Sai Dhiraj K. Inspired by the need for secure, reproducible scientific tools to ease atmospheric modeling for small scale applications. 
