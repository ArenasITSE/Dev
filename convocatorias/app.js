const convocatorias = [
{
    titulo: "CONCURSO DE OPOSICIÓN PARA LA PROMOCIÓN A PROFESOR ASOCIADO A",

    estado: "cerrada",

    fecha: "24 de Abril de 2026",

    periodo: "Del 24 al 29 de abril de 2026 (10:00 a 14:00 horas)",

    departamento: "Dirección General / Departamento de Capital Humano",

    descripcion:
    "Se convoca al personal docente al concurso de oposición de promoción de categoría a PROFESOR ASOCIADO A. Esta convocatoria tiene el propósito de fortalecer la investigación, el desarrollo tecnológico y el impulso a la innovación.",

    resultado:
    "Aquí puedes consultar el documento oficial con la resolución emitida por la Comisión Dictaminadora.",

    tipoResultado: "pdf",

    dictamen:{
        nombre:"Dictamen de la Comisión Dictaminadora",
        url:"assets/dictamen_asociado_a.pdf"
    },

    pdfs:[
        {
            nombre:"Ver Convocatoria",
            url:"assets/CONCURSO_OPOSICION_ASOCIADO_A_1-3.pdf"
        },
        {
            nombre:"ANEXO I",
            url:"assets/ANEXO_I_ASOCIADO_A.pdf"
        },
        {
            nombre:"ANEXO II",
            url:"assets/ANEXO_II_ASOCIADO_A.pdf"
        }
    ]
},

{
    titulo: "CONCURSO DE OPOSICIÓN EXTERNO PARA PROFESOR ASOCIADO B",

    estado: "Cerrada",

    fecha:"15 Mayo 2026",

    periodo:"15 al 30 Mayo 2026",

    departamento:"Capital Humano",

    descripcion:
    " Se convoca al concurso de oposición para reclutamiento de personal docente de categoría a PROFESOR ASOCIADO B.  <br> Esta convocatoria tiene el propósito de fortalecer la investigación, el desarrollo tecnológico y el impulso a la innovación. Está dirigida a profesores que cuenten con al menos 3 años de experiencia laboral y que cuenten con posgrado en un área afín al programa educativo ofertado.",
    tipoResultado:"tabla",

    ganadores:[
        {
            nombre:"Kevin Alejandro Avilés Betanzos",
            programa:"Posgrado"
        },
        {
            nombre:"Emmanuel de Jesús Chi Gutierrez",
            programa:"Ingeniería en Industrias Alimentarias"
        }
    ],

    pdfs:[
        {
            nombre:"Convocatoria",
            url:"assets/CONCURSO_EXTERNO_ASOCIADO_B_1-3.pdf"
        },
          {
            nombre:"ANEXO I",
            url:"assets/ANEXO_I_ASOCIADO_B.pdf"
        },
        {
            nombre:"ANEXO II",
            url:"assets/ANEXO_II_ASOCIADO_B.pdf"
        }
    ]
},

{
    titulo: 'CONCURSO DE OPOSICIÓN PARA LA PROMOCIÓN A PROFESOR ASOCIADO "B"',

    estado: "Cerrada",

    fecha: '18 de Marzo, 2026',

    periodo: 'Del 19 al 20 de Marzo de 2026 (10:00 a 14:00 horas)',

    departamento: 'Dirección General / Subdirección Académica de Investigación e Innovación',

    descripcion: `
        Se convoca al personal docente al concurso de oposición de promoción de categoría
        a PROFESOR ASOCIADO "B", en relación al cumplimiento de los criterios de la
        evaluación docente establecidos por el Tecnológico Nacional de México.
        <br><br>
        Esta convocatoria tiene el propósito fundamental de fortalecer la investigación,
        el desarrollo tecnológico y el impulso a la innovación en la institución.
        Está dirigida a profesores que cuenten con al menos 2 años de experiencia
        con contrato vigente en el modelo del Instituto Tecnológico Superior de Escárcega
        y que hayan obtenido el grado y cédula de Maestría en un área afín al programa
        educativo al que se encuentran adscritos.
    `,

    tipoResultado: "pdf",

    resultado:
    "Aquí puedes consultar el documento oficial con la resolución emitida por la Comisión Dictaminadora.",

    dictamen:{
        nombre:"Dictamen de la Comisión Dictaminadora",
        url:"assets/DICTAMEN DE COMISION DICTAMINADORA.pdf"
    },

    pdfs:[
        {
            nombre:"Ver Convocatoria",
            url:"assets/CONCURSO OPOSICION PARA PROMOCION A PROFESOR ASOCIADO B.pdf"
        },
        {
            nombre:"Ver Anexo",
            url:"assets/ANEXO CONVOCATORIA PROMOCION ASOCIADO B.pdf"
        }
    ]
}
];






const contenedor = document.getElementById("convocatorias");

convocatorias.forEach((item,index)=>{

    const estadoClase =
    item.estado.toLowerCase() === "abierta"
        ? "abierta"
        : "cerrada";

    const resultadosHTML = (()=>{

        if(item.tipoResultado === "tabla"){

            return `
            
            <div class="resultados">

                <div class="resultados-tag">
                    RESULTADOS
                </div>

                <h3>Ganadores del concurso</h3>

                <hr class="linea-resultados">

                <p class="texto-resultados">
                    Se comunica, con base en el Procedimiento del SGI para el Reclutamiento,
                    Selección y Contratación de Personal (ITSE-SGI-AD-PO-003) y en la
                    Convocatoria para Concurso de Oposición Externo para Reclutamiento
                    de personal docente de categoría Profesor Asociado "B", los
                    ganadores del proceso:
                </p>

                <table class="tabla-ganadores">

                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Programa Educativo</th>
                        </tr>
                    </thead>

                    <tbody>

                        ${item.ganadores.map(g=>`

                            <tr>
                                <td>${g.nombre}</td>
                                <td>${g.programa}</td>
                            </tr>

                        `).join('')}

                    </tbody>

                </table>

            </div>
            `;
        }

        if(item.tipoResultado === "pdf" && item.dictamen){

            return `
            
            <div class="resultados">

                <div class="resultados-tag">
                    RESULTADOS
                </div>

                <h3>Dictamen del concurso</h3>

                <p>
                    ${item.resultado}
                </p>

                <br>

                <a
                    href="${item.dictamen.url}"
                    target="_blank"
                    class="btn"
                >
                    ${item.dictamen.nombre} (PDF)
                </a>

            </div>
            `;
        }

        return "";

    })();

    const div = document.createElement("div");

    div.className = "convocatoria";

    div.innerHTML = `

    <div class="convocatoria-header">

        <div class="left">

            <span class="arrow">▶</span>

            <div class="titulo">
                ${item.titulo}
            </div>

        </div>

        <div class="estado ${estadoClase}">
            ${item.estado.toUpperCase()}
        </div>

    </div>

    <div class="content">

        <div class="grid">

            <div>
                <h4>Fecha de Publicación</h4>
                <p>${item.fecha}</p>
            </div>

            <div>
                <h4>Periodo de Recepción</h4>
                <p>${item.periodo}</p>
            </div>

            <div>
                <h4>Departamento</h4>
                <p>${item.departamento}</p>
            </div>

        </div>

        <div class="descripcion">
            ${item.descripcion}
        </div>

        ${resultadosHTML}

        <div class="documentacion">

            <h4>DOCUMENTACIÓN TÉCNICA</h4>

            <div class="botones">

                ${item.pdfs.map(pdf => `
                
                    <a
                        href="${pdf.url}"
                        target="_blank"
                        class="pdf"
                    >
                        ${pdf.nombre} (PDF)
                    </a>

                `).join("")}

            </div>

            <div class="estado-publicacion">
                Estado de la publicación:
                <strong>${item.estado.toUpperCase()}</strong>
            </div>

        </div>

    </div>
    `;

    contenedor.appendChild(div);

    if(index === 0){
        div.classList.add("active");
    }

});

document
.querySelectorAll(".convocatoria-header")
.forEach(header=>{

    header.addEventListener("click",()=>{

        const padre = header.parentElement;

        padre.classList.toggle("active");

    });

});