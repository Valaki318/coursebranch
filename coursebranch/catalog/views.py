import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Course, College
from pyvis.network import Network
from django.http import HttpResponse

def course_detail_view(request, code):
    course = get_object_or_404(Course, code=code)

    return render(request, "catalog/course_detail.html", {
        "course": course,
        "prereqs": course.prerequisites.all(),
        "postreqs": Course.objects.filter(prerequisites=course)
    })

def upload_catalog_view(request):
    colleges = College.objects.all()

    if request.method == "POST":
        college = College.objects.get(id=request.POST["college"])
        csv_file = request.FILES["csv_file"]

        # Read file once → store lines
        raw = csv_file.read().decode("utf-8").splitlines()

        # First pass — create course objects
        reader = csv.DictReader(raw)
        course_objects = {}

        for row in reader:
            course, _ = Course.objects.get_or_create(
                code=row["code"].strip(),
                defaults={
                    "name": row["name"].strip(),
                    "description": row["description"].strip(),
                    "instructor": row["instructor"].strip(),
                    "credits": int(row["credits"]),
                    "college": college,
                }
            )
            course_objects[row["code"].strip()] = course

        # Second pass — assign prerequisites
        reader = csv.DictReader(raw)  # ← re-read SAME list of strings

        for row in reader:
            course = course_objects[row["code"].strip()]
            prereqs = [c.strip() for c in row["prerequisites"].split(";") if c.strip()]
            for p in prereqs:
                if p in course_objects:
                    course.prerequisites.add(course_objects[p])

        return render(request, "catalog/upload_success.html")

    return render(request, "catalog/upload.html", {"colleges": colleges})

def course_tree_index_view(request):
    return render(request, "catalog/tree.html")

def course_tree_view(request):
    courses = Course.objects.all().prefetch_related("prerequisites")
    
    # Build PyVis network
    net = Network(
        height="90vh",
        width="100%",
        directed=True,
        bgcolor="#111111",
        font_color="white"
    )

    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "stabilization": { "iterations": 100 },
        "barnesHut": {
          "avoidOverlap": 0.2,
          "springLength": 160,
          "damping": 0.09
        }
      },
      "edges": {
        "arrows": { "to": { "enabled": true }},
        "color": "rgba(200,200,200,0.4)",
        "width": 2,
        "smooth": { "enabled": true }
      },
      "nodes": {
        "shape": "dot",
        "size": 20,
        "borderWidth": 2
      }
    }
    """)

    # Add nodes + edges
    for c in courses:
        net.add_node(
            c.code,
            label=f"{c.code}",
            title=c.name,
            color="#4da6ff"
        )
        for p in c.prerequisites.all():
            net.add_edge(p.code, c.code)

    # Always produce HTML
    html = net.generate_html(notebook=False)

    # Inject click handler
    html = html.replace(
        "</body>",
        """
        <script>
        document.addEventListener("DOMContentLoaded", function () {
            network.on("click", function(params) {
                if (params.nodes.length > 0) {
                    let code = params.nodes[0];
                    window.location.href = "/catalog/course/" + code + "/";
                }
            });
        });
        </script>
        </body>
        """
    )

    return HttpResponse(html)
